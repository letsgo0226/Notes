"""Offline-only falsifiability tests for the CLTP conceptual trading clock."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research' / 'cltp'))
from cltp import (  # noqa: E402
    PROGRAM, SYMBOL, MAX_ORDER_QUOTE, STOP_LOSS_REALIZED,
    ResearchInputError, backtest, decode_clock, load_candles,
)

PRICE = ['100','100','100','90','89','89','70','75','80','84','88','83',
         '60','59','58','57','70','75','79','81']
START = datetime(2026, 10, 13, tzinfo=timezone.utc)


def candles(*, sell_open='83', prices=None, next_day_at=None):
    prices = PRICE if prices is None else prices
    out = []
    for i, close in enumerate(prices):
        timestamp = START + timedelta(minutes=i)
        if next_day_at is not None and i >= next_day_at:
            timestamp += timedelta(days=1)
        out.append({'timestamp': timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'time': timestamp,
                    'open': Decimal(sell_open if i == 10 else (prices[i-1] if i else close)),
                    'close': Decimal(close)})
    return out


class CLTPOfflineTests(unittest.TestCase):
    def test_exact_program_and_two_step_invariant(self):
        table = decode_clock(PROGRAM)
        self.assertEqual(len(table), 4)
        for q in (0, 1):
            for a in (0, 1):
                self.assertEqual(table[(q, a)], (1-q, a, 1-2*q))
                q1, _, d1 = table[(q, a)]
                q2, _, d2 = table[(q1, a)]
                self.assertEqual((q2, d1 + d2), (q, 0))
        with self.assertRaises(ResearchInputError):
            decode_clock(1829)

    def test_signals_confirm_on_two_closed_bars_execute_next_open(self):
        rows = candles()
        result = backtest(rows)
        self.assertEqual(result['asset'], SYMBOL)
        self.assertEqual(result['mode'], 'OFFLINE_HISTORICAL_CANDLE_RESEARCH_ONLY')
        self.assertEqual(result['broker_calls'], 0)
        self.assertEqual(result['real_orders'], 0)
        self.assertEqual(result['live_order_permission'], 'DENIED')
        self.assertTrue(result['machine_two_step_identity_verified'])
        self.assertEqual(result['signals'][7]['phase'], 'VERIFY')
        self.assertTrue(result['signals'][7]['next_open_order_scheduled'])
        self.assertEqual(result['simulated_trades'][0]['side'], 'BUY')
        self.assertEqual(result['simulated_trades'][0]['decision_bar'], 7)
        self.assertEqual(result['simulated_trades'][0]['execution_bar'], 8)
        self.assertEqual(result['simulated_trades'][0]['price'], '75.0375')
        for trade in result['simulated_trades']:
            self.assertGreater(trade['execution_bar'], trade['decision_bar'])
            self.assertLessEqual(Decimal(trade['quote_notional_usdt']), MAX_ORDER_QUOTE)
            self.assertLessEqual(Decimal(trade['total_debit_usdt']), MAX_ORDER_QUOTE)
            self.assertLessEqual(Decimal(trade['fee_usdt']), MAX_ORDER_QUOTE)
        self.assertGreater(Decimal(result['fees_paid_usdt']), 0)

    def test_next_bar_price_gap_causes_loss_overshoot_and_daily_latch(self):
        result = backtest(candles(sell_open='65'))
        self.assertEqual(result['simulated_utc_stop_latches'], ['2026-10-13'])
        self.assertEqual([x['side'] for x in result['simulated_trades']], ['BUY','SELL'])
        self.assertLess(Decimal(result['simulated_trades'][1]['realized_pnl_usdt']), -STOP_LOSS_REALIZED)
        self.assertGreaterEqual(result['rejected_or_empty_intents'], 1)
        self.assertEqual(result['live_order_permission'], 'DENIED')

    def test_utc_rollover_resets_paper_halt_but_not_live_permission(self):
        result = backtest(candles(sell_open='65', next_day_at=12))
        self.assertEqual(result['simulated_utc_stop_latches'], ['2026-10-13'])
        self.assertTrue(any(x['timestamp'].startswith('2026-10-14') for x in result['simulated_trades']))
        self.assertEqual(result['live_order_permission'], 'DENIED')
        self.assertFalse(result['automated_live_trading'])

    def test_future_close_cannot_change_prior_fills(self):
        initial = candles()
        changed = deepcopy(initial)
        for i in range(11, len(changed)):
            changed[i]['close'] = Decimal('100000') if i % 2 else Decimal('0.1')
        old = backtest(initial)
        new = backtest(changed)
        # A close after bar 10 must not influence orders filled at bar <=10.
        self.assertEqual([x for x in old['simulated_trades'] if x['execution_bar'] <= 10],
                         [x for x in new['simulated_trades'] if x['execution_bar'] <= 10])

    def test_cannot_buy_at_current_signal_candle_close(self):
        report = backtest(candles(prices=PRICE[:8]))
        self.assertEqual(report['trade_count'], 0)
        self.assertTrue(report['unexecuted_last_bar_intent'])

    def test_csv_parsing_is_strict_and_local(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'candles.csv'
            with path.open('w', newline='', encoding='utf-8') as out:
                writer = csv.writer(out)
                writer.writerow(['timestamp', 'open', 'close'])
                for row in candles():
                    writer.writerow([row['timestamp'], str(row['open']), str(row['close'])])
            actual = load_candles(path)
            self.assertEqual(len(actual), 20)
            self.assertEqual(backtest(actual)['trade_count'], backtest(candles())['trade_count'])
            result = subprocess.run([sys.executable, str(ROOT/'research/cltp/cltp.py'),
                                     '--csv', str(path)], capture_output=True,
                                    text=True, timeout=15, check=True)
            import json
            obj = json.loads(result.stdout)
            self.assertEqual(obj['trade_count'], len(obj['simulated_trades']))
            self.assertEqual(obj['live_order_permission'], 'DENIED')
            # Corruption must not silently skip invalid rows.
            path.write_text('timestamp,open,close\n2026-10-13T00:00:00,100,100\n'*8)
            with self.assertRaises(ResearchInputError):
                load_candles(path)
            path.write_text('timestamp,open,close\n' +
                            ''.join(f'2026-10-13T00:0{i}:00Z,NaN,100\n' for i in range(7)))
            with self.assertRaises(ResearchInputError):
                load_candles(path)

    def test_no_order_at_all_for_constant_prices(self):
        r = backtest(candles(prices=['100']*12))
        self.assertEqual(r['trade_count'], 0)
        self.assertEqual(r['ending_equity_usdt'], '250')
        self.assertEqual(r['simulated_utc_stop_latches'], [])
        self.assertEqual(r['broker_calls'], 0)

    def test_input_list_validation_rejects_non_utc_and_nonfinite(self):
        rows = candles()
        rows[1]['time'] = rows[0]['time']
        with self.assertRaises(ResearchInputError):
            backtest(rows)
        rows = candles()
        rows[3]['close'] = Decimal('NaN')
        with self.assertRaises(ResearchInputError):
            backtest(rows)


if __name__ == '__main__':
    unittest.main()
