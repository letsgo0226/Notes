"""Manual Binance Spot LIMIT/FOK orders; no strategy or automatic submission.

Operator supplies every order. A durable journal records the client ID before
the single POST; uncertain results are reconciled with GET, never resubmitted.
"""
from contextlib import contextmanager
from hsi_spot_risk import enforce_order, restricted_order_limit, assert_live_release, review_report
from hsi_spot_pretrade_gate import ensure_schema, enforce_pretrade, status as daily_stop_status
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def amount(value):
    if not isinstance(value, str) or len(value) > 30 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
        raise ValueError('price and quantity must be positive decimal strings')
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise ValueError('amount must be positive and finite')
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('broker redirect rejected')


class BinanceOrders:
    def __init__(self, journal, manifest):
        self.journal = Path(journal)
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest
        self.lock = threading.Lock()
        self.broker_calls = 0
        self.credentials_verified = False
        self.account_result = None
        with self.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL, created REAL NOT NULL, submitted REAL, state TEXT NOT NULL, result TEXT)')
            ensure_schema(db)

    @contextmanager
    def database(self):
        db = sqlite3.connect(self.journal, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def status(self):
        with self.database() as db:
            local_stop = daily_stop_status(db)
        return {'broker': 'Binance Spot', 'execution': 'manual LIMIT/FOK only',
                'credentials_present': bool(os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_API_SECRET')),
                'credentials_verified': self.credentials_verified, 'live_armed': os.getenv('LIVE_ARMED', '0') == '1',
                'signed_account_read_verified': bool(self.account_result and self.account_result['signed_read_verified']),
                'spot_permission_verified': bool(self.account_result and self.account_result['spot_trading_permission_verified']),
                'account_check_status': self.account_result['status'] if self.account_result else 'NOT_REQUESTED',
                'dry_run': os.getenv('LIVE_DRY_RUN', '1') != '0',
                'kill_switch': os.getenv('HSI_ORDER_KILL', '1') != '0',
                'durable_journal': os.getenv('HSI_ORDER_JOURNAL_DURABLE', '0') == '1' and os.path.ismount(self.journal.parent),
                'operator_token_configured': bool(os.getenv('HSI_ORDER_CONTROL_TOKEN')),
                'max_quote_per_order': str(restricted_order_limit(os.getenv('MAX_QUOTE_PER_ORDER', '10'))),
                'daily_realized_loss_limit_usdt': '2',
                'daily_realized_pnl_status': local_stop['status'],
                'daily_loss_latch_review_only': local_stop['status'] == 'HALT_DAILY_LOSS_REVIEW_LATCHED',
                'live_release': 'BLOCKED_PENDING_SEPARATE_APPROVAL',
                'auto_strategy_promotion': False,
                'symbol_allowlist': [s for s in os.getenv('HSI_ORDER_SYMBOL_ALLOWLIST', 'BTCUSDT').split(',') if s == 'BTCUSDT'],
                'automatic_trading': False, 'notes_manifest_sha256': self.manifest}

    def broker(self, path, params=None, method='GET', signed=False):
        base = os.getenv('BINANCE_TRADE_BASE_URL', 'https://api.binance.com').rstrip('/')
        target = urllib.parse.urlsplit(base)
        if target.scheme != 'https' or target.hostname not in {'api.binance.com', 'testnet.binance.vision'} or target.netloc != target.hostname or target.path or target.query or target.fragment:
            raise ValueError('unapproved broker URL')
        parameters = dict(params or {})
        headers = {}
        if signed:
            key, secret = os.getenv('BINANCE_API_KEY', ''), os.getenv('BINANCE_API_SECRET', '')
            if not key or not secret:
                raise ValueError('Binance credentials are not configured')
            parameters.update(timestamp=int(time.time() * 1000), recvWindow=5000)
            headers['X-MBX-APIKEY'] = key
        query = urllib.parse.urlencode(parameters)
        if signed:
            query += '&signature=' + hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        data = query.encode() if method == 'POST' else None
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = urllib.request.Request(base + path + ('?' + query if method == 'GET' and query else ''), data=data, headers=headers, method=method)
        self.broker_calls += 1
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
            return json.loads(response.read(2 * 1024 * 1024))

    @staticmethod
    def read_error(exc):
        # Never expose the signed URL, API key, account payload, or broker text.
        result = {'type': type(exc).__name__}
        if isinstance(exc, urllib.error.HTTPError):
            result['http_status'] = exc.code
            try:
                data = json.loads(exc.read(4096))
                if isinstance(data, dict) and type(data.get('code')) is int:
                    result['broker_code'] = data['code']
            except (ValueError, TypeError):
                pass
        return result

    def account_check(self, request):
        """Signed GETs only; account/key permissions do not test an order."""
        if request.get('notes_manifest_sha256') != self.manifest:
            raise ValueError('Notes manifest mismatch')
        with self.lock:
            now = time.time()
            if self.account_result and now - self.account_result['checked_at'] < 60:
                return {**self.account_result, 'cached': True}
            result = {'status': 'UNRESOLVED', 'signed_read_verified': False,
                      'spot_trading_permission_verified': False,
                      'account_can_trade': None, 'api_spot_trading_enabled': None,
                      'checked_at': now, 'order_submission': False,
                      'test_order_verified': self.credentials_verified,
                      'notes_manifest_sha256': self.manifest}
            try:
                account = self.broker('/api/v3/account', {'omitZeroBalances': 'true'}, signed=True)
                if not isinstance(account, dict) or type(account.get('canTrade')) is not bool or not isinstance(account.get('accountType'), str):
                    raise ValueError('unexpected account response')
                result['signed_read_verified'] = True
                result['account_can_trade'] = account['canTrade']
                spot_account = account['accountType'] == 'SPOT'
                # Do not retain balances, UID, commissions, or the full response.
                del account
                if os.getenv('BINANCE_TRADE_BASE_URL', 'https://api.binance.com').rstrip('/') == 'https://testnet.binance.vision':
                    result['reason'] = 'Wallet permission endpoint is unavailable on Spot testnet'
                else:
                    restrictions = self.broker('/sapi/v1/account/apiRestrictions', signed=True)
                    if not isinstance(restrictions, dict) or type(restrictions.get('enableSpotAndMarginTrading')) is not bool:
                        raise ValueError('unexpected API permission response')
                    result['api_spot_trading_enabled'] = restrictions['enableSpotAndMarginTrading']
                    del restrictions
                    result['spot_trading_permission_verified'] = spot_account and result['account_can_trade'] and result['api_spot_trading_enabled']
                    result['status'] = 'PERMISSIONS_VERIFIED' if result['spot_trading_permission_verified'] else 'BLOCKED'
            except Exception as exc:
                result['error'] = self.read_error(exc)
            self.account_result = result
            return dict(result)

    def history_audit(self, request):
        """Operator-authorized, bounded signed GETs only; NEVER place orders.

        Separately opted-in by deployment config; safe standby is mandatory.
        Returns summary flags, not balances/UID/fills. No live-trade release.
        """
        if request.get('notes_manifest_sha256') != self.manifest:
            raise ValueError('Notes manifest mismatch')
        if request.get('acknowledge_read_only') is not True:
            raise ValueError('explicit read-only audit acknowledgement required')
        from hsi_binance_readonly_audit import read_only_audit
        if (os.getenv('LIVE_ARMED', '0') != '0'
                or os.getenv('LIVE_DRY_RUN', '1') != '1'
                or os.getenv('HSI_ORDER_KILL', '1') != '1'):
            return {**read_only_audit(self.broker, enabled=False),
                    'reason': 'UNSAFE_DEPLOYMENT_CONFIGURATION'}
        if os.getenv('HSI_READONLY_HISTORY_AUDIT_ENABLED', '0') != '1':
            return read_only_audit(self.broker, enabled=False)
        with self.lock:
            return read_only_audit(self.broker, enabled=True)

    def prepare(self, request):
        if request.get('notes_manifest_sha256') != self.manifest:
            raise ValueError('Notes manifest mismatch')
        symbol, side = request.get('symbol'), request.get('side')
        if symbol not in self.status()['symbol_allowlist'] or side not in {'BUY', 'SELL'}:
            raise ValueError('unsupported symbol or side')
        quantity, price = amount(request.get('quantity')), amount(request.get('price'))
        enforce_order(symbol, str(price), str(quantity), os.getenv('MAX_QUOTE_PER_ORDER', '10'))
        client_id = 'hsi' + uuid.uuid4().hex[:24]
        payload = {'symbol': symbol, 'side': side, 'type': 'LIMIT', 'timeInForce': 'FOK',
                   'quantity': format(quantity, 'f'), 'price': format(price, 'f'), 'newClientOrderId': client_id}
        digest = hashlib.sha256(canonical({'order': payload, 'manifest': self.manifest}).encode()).hexdigest()
        now = time.time()
        with self.database() as db:
            db.execute('INSERT INTO orders(id,payload,digest,created,state) VALUES(?,?,?,?,?)', (client_id, canonical(payload), digest, now, 'PREPARED'))
        return {'status': 'PREPARED', 'ticket': client_id, 'order_sha256': digest, 'order': payload,
                'quote_notional': format(quantity * price, 'f'), 'expires_at': now + 120,
                'order_submission': False, 'notes_manifest_sha256': self.manifest}

    def ticket(self, request, fresh=True):
        with self.database() as db:
            row = db.execute('SELECT * FROM orders WHERE id=?', (request.get('ticket'),)).fetchone()
        if not row or not hmac.compare_digest(str(request.get('order_sha256', '')), row['digest']):
            raise ValueError('unknown ticket or changed order')
        if fresh and time.time() > row['created'] + 120:
            raise ValueError('order ticket expired; prepare a new explicit order')
        return dict(row), json.loads(row['payload'])

    def verify_filters(self, payload):
        info = self.broker('/api/v3/exchangeInfo', {'symbol': payload['symbol']})['symbols'][0]
        if info.get('status') != 'TRADING' or not info.get('isSpotTradingAllowed') or 'LIMIT' not in info.get('orderTypes', []):
            raise ValueError('symbol is not available for Spot LIMIT trading')
        filters = {r['filterType']: r for r in info['filters']}
        quantity, price = amount(payload['quantity']), amount(payload['price'])
        for name, value, minimum, maximum, quantum in (('LOT_SIZE', quantity, 'minQty', 'maxQty', 'stepSize'), ('PRICE_FILTER', price, 'minPrice', 'maxPrice', 'tickSize')):
            rule = filters[name]
            low, high, step = (Decimal(rule[k]) for k in (minimum, maximum, quantum))
            if (low and value < low) or (high and value > high) or (step and value % step):
                raise ValueError('order violates ' + name)
        for name in ('MIN_NOTIONAL', 'NOTIONAL'):
            if name in filters:
                rule = filters[name]
                notional = quantity * price
                if notional < Decimal(rule['minNotional']) or (Decimal(rule.get('maxNotional', '0')) and notional > Decimal(rule['maxNotional'])):
                    raise ValueError('order violates ' + name)

    def test(self, request):
        with self.lock:
            row, payload = self.ticket(request)
            if row['state'] == 'TESTED':
                return {'status': 'TESTED', 'order_submission': False, 'ticket': row['id']}
            if row['state'] != 'PREPARED':
                raise ValueError('ticket already used; reconcile without resubmission')
            self.verify_filters(payload)
            self.broker('/api/v3/order/test', payload, 'POST', True)
            self.credentials_verified = True
            with self.database() as db:
                db.execute('UPDATE orders SET state=? WHERE id=?', ('TESTED', row['id']))
            return {'status': 'TESTED', 'order_submission': False, 'matching_engine_used': False, 'ticket': row['id']}

    def submit(self, request):
        with self.lock:
            row, payload = self.ticket(request)
            settings = self.status()
            if request.get('confirm_live_order') is not True:
                raise ValueError('this exact order requires explicit live confirmation')
            if not settings['live_armed'] or settings['dry_run'] or settings['kill_switch'] or not settings['durable_journal'] or not settings['operator_token_configured'] or not settings['credentials_present']:
                raise ValueError('live order is blocked by the deployment configuration')
            # The independent SQLite daily stop/unknown gate also blocks sends,
            # including if a future developer loosens the code-release gate.
            with self.database() as db:
                enforce_pretrade(db)
            assert_live_release()  # independent, separately reviewed release still required
            if row['state'] != 'TESTED':
                raise ValueError('order must pass broker test once; used orders are never resubmitted')
            if amount(payload['quantity']) * amount(payload['price']) > amount(os.getenv('MAX_QUOTE_PER_ORDER', '10')):
                raise ValueError('order exceeds current quote limit')
            if payload['symbol'] not in settings['symbol_allowlist']:
                raise ValueError('symbol no longer allowed')
            self.verify_filters(payload)
            now = time.time()
            with self.database() as db:
                uncertain = db.execute("SELECT id FROM orders WHERE state IN ('SUBMITTING','UNKNOWN') LIMIT 1").fetchone()
                if uncertain:
                    raise ValueError('an earlier submission must be reconciled before another order')
                recent = db.execute("SELECT payload FROM orders WHERE submitted>=?", (now - 86400,)).fetchall()
                if len(recent) >= int(os.getenv('HSI_MAX_ORDERS_PER_DAY', '3')):
                    raise ValueError('daily order count limit reached')
                db.execute('UPDATE orders SET state=?,submitted=? WHERE id=?', ('SUBMITTING', now, row['id']))
            # The journal transaction above is committed before the external POST.
            try:
                result = self.broker('/api/v3/order', payload, 'POST', True)
                state = 'SUBMITTED'
            except Exception as exc:
                result = {'error': type(exc).__name__, 'instruction': 'Query this client order ID; never retry the order POST'}
                state = 'UNKNOWN'
            with self.database() as db:
                db.execute('UPDATE orders SET state=?,result=? WHERE id=?', (state, canonical(result), row['id']))
            return {'status': state, 'ticket': row['id'], 'order_submission_attempted': True, 'result': result}

    def reconcile(self, request):
        row, payload = self.ticket(request, fresh=False)
        if row['state'] not in {'SUBMITTING', 'UNKNOWN', 'SUBMITTED', 'RECONCILED'}:
            raise ValueError('no live submission to reconcile')
        result = self.broker('/api/v3/order', {'symbol': payload['symbol'], 'origClientOrderId': row['id']}, signed=True)
        with self.database() as db:
            db.execute('UPDATE orders SET state=?,result=? WHERE id=?', ('RECONCILED', canonical(result), row['id']))
        return {'status': 'RECONCILED', 'ticket': row['id'], 'result': result, 'order_submission_attempted': False}
