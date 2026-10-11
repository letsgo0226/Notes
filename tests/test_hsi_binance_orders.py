"""Broker calls are mocked; tests never place real or testnet orders."""
from contextlib import contextmanager
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hsi_binance_orders import BinanceOrders

MANIFEST = 'a' * 64
INFO = {'symbols': [{'status': 'TRADING', 'isSpotTradingAllowed': True, 'orderTypes': ['LIMIT'], 'filters': [
    {'filterType': 'LOT_SIZE', 'minQty': '0.001', 'maxQty': '100', 'stepSize': '0.001'},
    {'filterType': 'PRICE_FILTER', 'minPrice': '0.01', 'maxPrice': '1000000', 'tickSize': '0.01'},
    {'filterType': 'MIN_NOTIONAL', 'minNotional': '5'}]}]}


class ManualOrderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'orders.sqlite'
        self.orders = BinanceOrders(self.path, MANIFEST)
        self.env = patch.dict(os.environ, {'LIVE_ARMED': '0', 'LIVE_DRY_RUN': '1', 'HSI_ORDER_KILL': '1',
            'HSI_ORDER_JOURNAL_DURABLE': '1', 'HSI_ORDER_CONTROL_TOKEN': 'test-only',
            'BINANCE_API_KEY': 'test-only', 'BINANCE_API_SECRET': 'trader42-selftest', 'BINANCE_TRADE_BASE_URL': 'https://api.binance.com',
            'HSI_ORDER_SYMBOL_ALLOWLIST': 'BTCUSDT', 'MAX_QUOTE_PER_ORDER': '10', 'HSI_MAX_ORDERS_PER_DAY': '3'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def prepare(self, **changes):
        return self.orders.prepare({'symbol': 'BTCUSDT', 'side': 'BUY', 'price': '1000', 'quantity': '0.005',
                                    'notes_manifest_sha256': MANIFEST, **changes})

    @contextmanager
    def armed(self):
        with patch.dict(os.environ, {'LIVE_ARMED': '1', 'LIVE_DRY_RUN': '0', 'HSI_ORDER_KILL': '0'}), patch('os.path.ismount', return_value=True):
            yield

    def test_prepare_is_offline_and_enforces_explicit_fields(self):
        with patch.object(self.orders, 'broker') as broker:
            ticket = self.prepare()
            self.assertEqual(ticket['order']['timeInForce'], 'FOK')
            self.assertFalse(ticket['order_submission'])
            for changes in ({'price': 'NaN'}, {'quantity': 0.1}, {'quantity': '0.1'}, {'symbol': 'ETHUSDT'}, {'notes_manifest_sha256': 'bad'}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.prepare(**changes)
            broker.assert_not_called()

    def test_changed_ticket_expiry_and_disabled_live_never_post(self):
        ticket = self.prepare()
        with patch.object(self.orders, 'broker') as broker:
            with self.assertRaises(ValueError):
                self.orders.submit({**ticket, 'confirm_live_order': True})
            with self.assertRaises(ValueError):
                self.orders.test({**ticket, 'order_sha256': 'changed'})
            with patch('time.time', return_value=ticket['expires_at'] + 1), self.assertRaises(ValueError):
                self.orders.test(ticket)
            broker.assert_not_called()

    def test_broker_test_does_not_use_order_endpoint(self):
        ticket = self.prepare()
        with patch.object(self.orders, 'broker', side_effect=[INFO, {}]) as broker:
            self.assertEqual(self.orders.test(ticket)['status'], 'TESTED')
            self.assertEqual([c.args[0] for c in broker.call_args_list], ['/api/v3/exchangeInfo', '/api/v3/order/test'])
            self.assertTrue(self.orders.credentials_verified)

    def test_exchange_tick_and_notional_fail_before_test_post(self):
        for changes in ({'price': '1000.001'}, {'quantity': '0.004'}):
            ticket = self.prepare(**changes)
            with patch.object(self.orders, 'broker', return_value=INFO) as broker, self.assertRaises(ValueError):
                self.orders.test(ticket)
            self.assertEqual(broker.call_count, 1)

    def test_one_live_post_survives_restart_and_duplicate_is_blocked(self):
        ticket = self.prepare()
        with patch.object(self.orders, 'broker', side_effect=[INFO, {}]):
            self.orders.test(ticket)
        with self.armed(), patch.object(self.orders, 'broker', side_effect=[INFO, {'orderId': 123}]) as broker:
            result = self.orders.submit({**ticket, 'confirm_live_order': True})
            self.assertEqual(result['status'], 'SUBMITTED')
            self.assertEqual(broker.call_args_list[-1].args[:3], ('/api/v3/order', ticket['order'], 'POST'))
        restarted = BinanceOrders(self.path, MANIFEST)
        with self.armed(), patch.object(restarted, 'broker') as broker, self.assertRaises(ValueError):
            restarted.submit({**ticket, 'confirm_live_order': True})
        broker.assert_not_called()

    def test_network_uncertainty_is_journaled_and_blocks_new_orders(self):
        ticket = self.prepare()
        with patch.object(self.orders, 'broker', side_effect=[INFO, {}]):
            self.orders.test(ticket)
        with self.armed(), patch.object(self.orders, 'broker', side_effect=[INFO, TimeoutError()]):
            self.assertEqual(self.orders.submit({**ticket, 'confirm_live_order': True})['status'], 'UNKNOWN')
        next_ticket = self.prepare()
        with patch.object(self.orders, 'broker', side_effect=[INFO, {}]):
            self.orders.test(next_ticket)
        with self.armed(), patch.object(self.orders, 'broker', return_value=INFO) as broker, self.assertRaises(ValueError):
            self.orders.submit({**next_ticket, 'confirm_live_order': True})
        self.assertEqual(broker.call_count, 1)
        with patch.object(self.orders, 'broker', return_value={'orderId': 123}) as broker:
            self.orders.reconcile(ticket)
        self.assertTrue(broker.call_args.kwargs['signed'])
        self.assertEqual(broker.call_args.args[0], '/api/v3/order')

    def test_live_requires_confirmation_and_actual_mount(self):
        ticket = self.prepare()
        with self.armed(), patch.object(self.orders, 'broker') as broker, self.assertRaises(ValueError):
            self.orders.submit(ticket)
        broker.assert_not_called()
        with patch('os.path.ismount', return_value=False):
            self.assertFalse(self.orders.status()['durable_journal'])

    def test_signer_matches_known_vector_and_rejects_other_hosts(self):
        with patch('time.time', return_value=1700000000), patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(b'{}')
            self.orders.broker('/api/v3/order/test', {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quoteOrderQty': 10}, 'POST', True)
            request = opener.return_value.open.call_args.args[0]
            self.assertTrue(request.data.decode().endswith('signature=d719973baa307154388aa79938ca300dc1b5a3582564206134bf4bb1bddadf77'))
        with patch.dict(os.environ, {'BINANCE_TRADE_BASE_URL': 'https://evil.example'}), patch('urllib.request.build_opener') as opener, self.assertRaises(ValueError):
            self.orders.broker('/api/v3/account', signed=True)
        opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
