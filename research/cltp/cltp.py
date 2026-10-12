#!/usr/bin/env python3
"""COSMIC_LOVE Trading Protocol (CLTP): OFFLINE, synthetic-candle research only.

Uses P=55067263 purely as a two-stage observation/review clock. A separate
simple mean-reversion hypothesis produces candidate signals; neither the TM
nor this strategy has a demonstrated trading advantage. No network access,
Binance imports, credentials, persistence, deployment or actual orders.

Input: bounded local CSV with timestamp,open,close in UTC; each row is a
COMPLETED candle. A candidate confirmed at bar i CLOSE executes, at earliest,
at i+1 OPEN. Costs and a conservative UTC realized-loss stop are simulated.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path
import re
import sys

PROGRAM = 55067263
PROTOCOL = 'HSI-CLTP-OFFLINE-RESEARCH/1'
SYMBOL = 'BTCUSDT'
MAX_ORDER_QUOTE = Decimal('50')
MAX_POSITION_MARK_VALUE = Decimal('50')
STOP_LOSS_REALIZED = Decimal('2')
MAX_INPUT_BYTES = 2_000_000
MAX_CANDLES = 20_000
# Fixed conservative paper-only assumptions (not Binance exchange filters).
FEE_BPS = Decimal('10')
SLIPPAGE_BPS = Decimal('5')
INITIAL_USDT = Decimal('250')
MEAN_WINDOW = 3
THRESHOLD = Decimal('0.01')
_DECIMAL = re.compile(r'[0-9]+(?:\.[0-9]+)?\Z')
_TIMESTAMP = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z')


class ResearchInputError(ValueError):
    pass


def decimal_value(text):
    if not isinstance(text, str) or len(text) > 40 or not _DECIMAL.fullmatch(text):
        raise ResearchInputError('INVALID_PRICE_FORMAT')
    n = Decimal(text)
    if not n.is_finite() or not Decimal('0') < n <= Decimal('1e9'):
        raise ResearchInputError('INVALID_PRICE_RANGE')
    return n


def decimal_string(value):
    # Preserve exact Decimal digits; .normalize() may use ambient precision.
    s = format(value, 'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s


def decode_clock(program=PROGRAM):
    """Exact integer decoding of the user's 2-state, 2-symbol TM."""
    from math import isqrt
    if type(program) is not int or program < 0:
        raise ResearchInputError('INVALID_TM_PROGRAM')
    v = (isqrt(8 * program + 1) - 1) // 2
    c = program - v * (v + 1) // 2
    k = v - c + 1
    if k != 2:
        raise ResearchInputError('INVALID_TM_STATE_SPACE')
    K = k + 1
    B = 4 * K
    table = {}
    for q in (0, 1):
        for a in (0, 1):
            u = c // (B ** (2 * q + a)) % B
            z, r = divmod(u, K)
            table[(q, a)] = (r, z // 2, 2 * (z % 2) - 1)
            if table[(q, a)] != (1 - q, a, 1 - 2 * q):
                raise ResearchInputError('TM_TRANSITION_DEFECT')
    return table


def load_candles(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ResearchInputError('MISSING_LINKED_OR_OVERSIZE_CSV')
    try:
        with path.open('r', encoding='utf-8-sig', newline='') as src:
            reader = csv.DictReader(src, strict=True)
            if reader.fieldnames != ['timestamp', 'open', 'close']:
                raise ResearchInputError('CSV_REQUIRES_TIMESTAMP_OPEN_CLOSE')
            candles = []
            prior = None
            for row in reader:
                if len(candles) >= MAX_CANDLES:
                    raise ResearchInputError('CSV_TOO_MANY_CANDLES')
                if None in row or not isinstance(row.get('timestamp'), str):
                    raise ResearchInputError('INVALID_CSV_ROW')
                ts = row['timestamp']
                if not _TIMESTAMP.fullmatch(ts):
                    raise ResearchInputError('TIMESTAMP_MUST_BE_UTC_Z')
                try:
                    time = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                except ValueError as exc:
                    raise ResearchInputError('INVALID_TIMESTAMP') from exc
                if prior is not None and time <= prior:
                    raise ResearchInputError('CANDLE_TIME_NOT_STRICTLY_ASCENDING')
                prior = time
                candles.append({'timestamp': ts, 'time': time,
                                'open': decimal_value(row['open']),
                                'close': decimal_value(row['close'])})
            if len(candles) < 7:
                raise ResearchInputError('AT_LEAST_SEVEN_CANDLES_REQUIRED')
            return candles
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ResearchInputError('CSV_READ_FAILED') from exc


def signal(closes):
    """Unoptimized, falsifiable hypothesis; no prediction or guarantee."""
    if len(closes) < MEAN_WINDOW:
        return 'HOLD'
    avg = sum(closes[-MEAN_WINDOW:]) / MEAN_WINDOW
    last = closes[-1]
    if last < avg * (1 - THRESHOLD):
        return 'BUY'
    if last > avg * (1 + THRESHOLD):
        return 'SELL'
    return 'HOLD'


def backtest(candles):
    """Paper ledger: signal uses CLOSED bars; fills use NEXT bar's OPEN.

    Never call an exchange, grant live trading authority, or infer official
    exchange filters / taxes / completeness from these local candle rows.
    """
    table = decode_clock()
    if not isinstance(candles, list) or len(candles) < 7 or len(candles) > MAX_CANDLES:
        raise ResearchInputError('INVALID_CANDLE_SET')
    # Guard public Python entry point against malformed injected candle lists.
    last_time = None
    for row in candles:
        if (not isinstance(row, dict) or not isinstance(row.get('time'), datetime)
                or row['time'].utcoffset() is None or row['time'].utcoffset().total_seconds() != 0
                or not isinstance(row.get('timestamp'), str)
                or any(type(row.get(key)) is not Decimal or not row[key].is_finite()
                       or row[key] <= 0 for key in ('open', 'close'))
                or (last_time is not None and row['time'] <= last_time)):
            raise ResearchInputError('INVALID_CANDLE_SET')
        last_time = row['time']

    with localcontext() as ctx:
        ctx.prec = 90
        cash, btc, lots = INITIAL_USDT, Decimal(0), []
        fees_paid = Decimal(0)
        cumulative_realized = Decimal(0)
        realized_by_day = {}
        halted_days = set()
        trades, signals, equity = [], [], []
        closes = []
        q, h = 0, 0
        observed = None
        pending = None
        no_fill_count = 0
        clipped_count = 0
        for bar_index, row in enumerate(candles):
            ts, day, candle_open, close = (row['timestamp'], row['time'].date().isoformat(),
                                            row['open'], row['close'])
            # Pending decision was made using only PRIOR fully closed candles.
            if pending is not None:
                direction, decision_index, decision_ts = pending
                if decision_index >= bar_index:
                    raise AssertionError('LOOKAHEAD_PREVENTION_DEFECT')
                pending = None
                if day in halted_days:
                    no_fill_count += 1
                else:
                    slip = SLIPPAGE_BPS / Decimal(10000)
                    fee_rate = FEE_BPS / Decimal(10000)
                    execution = candle_open * ((1 + slip) if direction == 'BUY' else (1 - slip))
                    max_quote = MAX_ORDER_QUOTE
                    if direction == 'BUY':
                        # Quoted 50 USDT includes fee in this simulation.
                        inventory_capacity = MAX_POSITION_MARK_VALUE - btc * execution
                        notional = min(max_quote / (1 + fee_rate), cash / (1 + fee_rate),
                                       inventory_capacity)
                        if notional > 0:
                            qty = notional / execution
                            fee = notional * fee_rate
                            paid = notional + fee
                            if paid > MAX_ORDER_QUOTE or paid > cash:
                                raise AssertionError('BUY_NOTIONAL_BUDGET_DEFECT')
                            cash -= paid
                            btc += qty
                            lots.append([qty, paid])
                            fees_paid += fee
                            trades.append({'side': 'BUY', 'decision_bar': decision_index,
                                           'decision_timestamp': decision_ts,
                                           'execution_bar': bar_index, 'timestamp': ts,
                                           'price': decimal_string(execution),
                                           'btc_quantity': decimal_string(qty),
                                           'quote_notional_usdt': decimal_string(notional),
                                           'total_debit_usdt': decimal_string(paid),
                                           'fee_usdt': decimal_string(fee),
                                           'realized_pnl_usdt': '0'})
                        else:
                            no_fill_count += 1
                    elif direction == 'SELL':
                        qty = min(btc, max_quote / execution)
                        if qty > 0:
                            notional = qty * execution
                            fee = notional * fee_rate
                            receipts = notional - fee
                            disposed = qty
                            basis = Decimal(0)
                            while disposed > 0:
                                if not lots:
                                    raise AssertionError('FIFO_COST_BASIS_MISSING')
                                lotqty, lotcost = lots[0]
                                partqty = min(disposed, lotqty)
                                partcost = lotcost if partqty == lotqty else (lotcost * partqty / lotqty)
                                basis += partcost
                                disposed -= partqty
                                lotqty -= partqty
                                if lotqty == 0:
                                    lots.pop(0)
                                else:
                                    lots[0] = [lotqty, lotcost - partcost]
                            btc -= qty
                            cash += receipts
                            fees_paid += fee
                            pnl = receipts - basis
                            cumulative_realized += pnl
                            realized_by_day[day] = realized_by_day.get(day, Decimal(0)) + pnl
                            if realized_by_day[day] <= -STOP_LOSS_REALIZED:
                                halted_days.add(day)
                            trades.append({'side': 'SELL', 'decision_bar': decision_index,
                                           'decision_timestamp': decision_ts,
                                           'execution_bar': bar_index, 'timestamp': ts,
                                           'price': decimal_string(execution),
                                           'btc_quantity': decimal_string(qty),
                                           'quote_notional_usdt': decimal_string(notional),
                                           'total_debit_usdt': '0',
                                           'fee_usdt': decimal_string(fee),
                                           'realized_pnl_usdt': decimal_string(pnl)})
                        else:
                            no_fill_count += 1
                    else:
                        raise AssertionError('INVALID_PENDING_DIRECTION')

            closes.append(close)
            sig = signal(closes)
            phase = 'OBSERVE' if q == 0 else 'VERIFY'
            if phase == 'OBSERVE':
                observed = sig
            else:
                if observed == sig and sig != 'HOLD':
                    # No action at this candle's close: schedule next open.
                    pending = (sig, bar_index, ts)
                else:
                    clipped_count += 1
            signals.append({'bar': bar_index, 'timestamp': ts,
                            'phase': phase, 'candidate': sig,
                            'next_open_order_scheduled': bool(pending and pending[1] == bar_index)})
            # Verify original TM transition, independent of financial state.
            r, written, motion = table[(q, 0)]
            if (r, written, motion) != (1-q, 0, 1-2*q):
                raise AssertionError('TM_TRANSITION_DEFECT')
            q = r
            h += motion
            if q == 0 and h != 0:
                raise AssertionError('TM_CYCLE_DEFECT')
            # The market ledger is not reset when the TM returns to q=0.
            equity.append(cash + btc * close)
        if q not in (0, 1):
            raise AssertionError('TM_STATE_DEFECT')
        ending_equity = equity[-1]
        peak = equity[0]
        worst_drawdown = Decimal(0)
        for point in equity:
            peak = max(peak, point)
            worst_drawdown = max(worst_drawdown, peak - point)
        return {
            'protocol': PROTOCOL,
            'mode': 'OFFLINE_HISTORICAL_CANDLE_RESEARCH_ONLY',
            'machine_program': PROGRAM, 'machine_two_step_identity_verified': True,
            'strategy_hypothesis': 'TWO_CLOSE_CONSECUTIVE_MEAN_REVERSION_SIGNALS',
            'asset': SYMBOL, 'input_bars': len(candles),
            'assumptions': {'initial_usdt': decimal_string(INITIAL_USDT),
                            'fee_bps': decimal_string(FEE_BPS),
                            'slippage_bps': decimal_string(SLIPPAGE_BPS),
                            'max_order_total_quote_usdt': decimal_string(MAX_ORDER_QUOTE),
                            'max_initial_position_mark_usdt': decimal_string(MAX_POSITION_MARK_VALUE),
                            'daily_realized_loss_stop_usdt': decimal_string(STOP_LOSS_REALIZED),
                            'bar_execution': 'NEXT_BAR_OPEN_AFTER_SIGNAL_CONFIRMATION',
                            'utc_day': True},
            'signals': signals, 'simulated_trades': trades,
            'trade_count': len(trades),
            'rejected_or_empty_intents': no_fill_count,
            'unconfirmed_signal_pairs': clipped_count,
            'unexecuted_last_bar_intent': bool(pending),
            'fees_paid_usdt': decimal_string(fees_paid),
            'ending_cash_usdt': decimal_string(cash),
            'ending_btc': decimal_string(btc),
            'ending_equity_usdt': decimal_string(ending_equity),
            'net_equity_change_usdt': decimal_string(ending_equity - INITIAL_USDT),
            'candidate_realized_pnl_usdt': decimal_string(cumulative_realized),
            'simulated_realized_pnl_by_utc_day': {k: decimal_string(v)
                                                  for k,v in sorted(realized_by_day.items())},
            'simulated_utc_stop_latches': sorted(halted_days),
            'max_observed_mark_to_market_drawdown_usdt': decimal_string(worst_drawdown),
            'broker_reconciled': False, 'broker_calls': 0,
            'real_orders': 0, 'live_order_permission': 'DENIED',
            'automated_live_trading': False,
            'warnings': [
                'Historical synthetic/example candles are not independently authenticated BTCUSDT market data.',
                'One fixed illustrative signal rule; no out-of-sample alpha or statistical significance established.',
                'Next-open fills, slippage and USDT-only fees are assumptions, not exchange execution guarantees.',
                'Simulation omits exchange LOT_SIZE, price ticks, minimum order notional, taxes and deposits.',
                'Simulated 2 USDT realized-loss stopping cannot cap gaps, slippage or unrealized drawdown.',
                'The reversible TM clock does not imply reversible prices or trades.',
                'No Binance broker calls, keys, orders or live-risk release exists in this module.',
            ],
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True, type=Path,
                        help='locally supplied, historical completed UTC candle CSV')
    args = parser.parse_args(argv)
    try:
        output = backtest(load_candles(args.csv))
    except (ResearchInputError, OSError, InvalidOperation) as exc:
        parser.exit(2, 'CLTP_RESEARCH_REJECTED: ' + type(exc).__name__ + ': ' + str(exc) + '\n')
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
