"""Compare two redacted BTCUSDT trade fingerprints offline; NEVER authorize.

This is a *consistency* check between separately supplied JSON summaries.
A matching hash cannot authenticate either input, establish lifetime history,
validate initial BTC cost basis, or authorize a real Spot order. Both original
data sources and full account movements require independent verification.
"""
import json
from pathlib import Path
import re

from hsi_binance_readonly_audit import PROTOCOL as AUDIT_PROTOCOL
from hsi_spot_ledger import PROTOCOL as LEDGER_PROTOCOL
from hsi_spot_trade_digest import PROTOCOL as DIGEST_PROTOCOL

PROTOCOL = "HSI-TRADER42-BOUNDED-WINDOW-CROSSCHECK/1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _deny(reason):
    return {
        "protocol": PROTOCOL,
        "status": "UNKNOWN_FAIL_CLOSED",
        "reason": reason,
        "bounded_window_digest_matches": False,
        "broker_reconciled": False,
        "daily_pnl_verified": False,
        "live_order_permission": "DENIED",
        "real_order_submissions": 0,
    }


def crosscheck(snapshot, replay):
    """Only compare normalized metadata from *independently provided* inputs."""
    if not isinstance(snapshot, dict) or not isinstance(replay, dict):
        return _deny("INVALID_EVIDENCE")
    if snapshot.get("protocol") != AUDIT_PROTOCOL or replay.get("protocol") != LEDGER_PROTOCOL:
        return _deny("INCOMPATIBLE_EVIDENCE_PROTOCOL")
    if (snapshot.get("status") != "READ_ONLY_SNAPSHOT_UNVERIFIED"
            or replay.get("status") != "LOCAL_REPLAY_ONLY"):
        return _deny("UNRESOLVED_EVIDENCE")
    if (snapshot.get("symbol") != "BTCUSDT"
            or snapshot.get("utc_day") != replay.get("utc_day")
            or type(snapshot.get("utc_day")) is not str):
        return _deny("MISMATCHED_SYMBOL_OR_UTC_DAY")
    if (snapshot.get("trade_fingerprint_scheme") != DIGEST_PROTOCOL
            or replay.get("trade_fingerprint_scheme") != DIGEST_PROTOCOL):
        return _deny("INCOMPATIBLE_FINGERPRINT_SCHEME")
    snapshot_digest = snapshot.get("trade_fingerprint_sha256")
    replay_digest = replay.get("trade_fingerprint_sha256")
    if (not isinstance(snapshot_digest, str) or not _SHA256.fullmatch(snapshot_digest)
            or not isinstance(replay_digest, str) or not _SHA256.fullmatch(replay_digest)):
        return _deny("INVALID_FINGERPRINT")
    if snapshot_digest != replay_digest:
        return _deny("TRADE_FINGERPRINT_MISMATCH")
    # These are basic accounting sanity checks; full brokerage proof is absent.
    count = snapshot.get("trade_count")
    buys = snapshot.get("buy_fill_count")
    sells = snapshot.get("sell_fill_count")
    if (any(type(x) is not int for x in (count, buys, sells))
            or not 0 <= count < 1000
            or buys < 0 or sells < 0 or buys + sells != count
            or replay.get("fill_count") != count
            or replay.get("buy_fills_today") != buys
            or replay.get("sell_fills_today") != sells
            or replay.get("all_fills_in_requested_utc_day") is not True):
        return _deny("INCONSISTENT_DAILY_FILL_COVERAGE")
    if (type(snapshot.get("snapshot_ms")) is not int
            or replay.get("snapshot_ms") != snapshot["snapshot_ms"]):
        return _deny("MISMATCHED_SNAPSHOT_TIME")
    if (snapshot.get("signed_reads") != 4
            or snapshot.get("broker_reconciled") is not False
            or snapshot.get("daily_pnl_verified") is not False
            or snapshot.get("live_order_permission") != "DENIED"
            or replay.get("broker_reconciled") is not False
            or replay.get("broker_requests") != 0
            or replay.get("live_order_permission") != "DENIED"):
        return _deny("INCONSISTENT_READ_ONLY_ATTESTATIONS")
    if snapshot.get("api_spot_trading_enabled") is not False:
        return _deny("SPOT_TRADE_PERMISSION_MUST_REMAIN_DISABLED")
    if snapshot.get("open_orders_present") is not False or snapshot.get("open_order_count") != 0:
        return _deny("OPEN_ORDERS_NOT_RECONCILED")
    if snapshot.get("non_usdt_btc_fee_present") is not False:
        return _deny("UNPRICED_COMMISSION_ASSETS")
    if type(replay.get("stop_threshold_reached_during_replay")) is not bool:
        return _deny("MISSING_STOP_THRESHOLD_EVIDENCE")
    return {
        "protocol": PROTOCOL,
        "status": "BOUNDED_DIGEST_MATCH_ONLY_NOT_RECONCILED",
        "symbol": "BTCUSDT",
        "utc_day": snapshot["utc_day"],
        "bounded_window_digest_matches": True,
        "matching_fill_count": count,
        "stop_threshold_reached_in_unverified_replay": replay["stop_threshold_reached_during_replay"],
        "broker_reconciled": False,
        "daily_pnl_verified": False,
        "opening_cost_basis_verified": False,
        "all_symbols_and_transfers_verified": False,
        "exchange_origin_authenticated_by_this_file": False,
        "live_order_permission": "DENIED",
        "real_order_submissions": 0,
        "reason": "Matching digests do not prove that a submitted snapshot is authentic, complete, or sufficient for risk release.",
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True,
                   help="locally held redacted signed-GET summary, not keys")
    p.add_argument("--ledger-report", type=Path, required=True,
                   help="locally held offline FIFO report, not credentials")
    a = p.parse_args()
    try:
        if (not a.snapshot.is_file() or not a.ledger_report.is_file()
                or a.snapshot.stat().st_size > 100000
                or a.ledger_report.stat().st_size > 100000):
            raise ValueError("INVALID_OR_OVERSIZED_FILE")
        snapshot = json.loads(a.snapshot.read_text(encoding="utf-8"))
        ledger = json.loads(a.ledger_report.read_text(encoding="utf-8"))
        result = crosscheck(snapshot, ledger)
    except (ValueError, OSError, UnicodeError):
        result = _deny("INVALID_OFFLINE_INPUT")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
