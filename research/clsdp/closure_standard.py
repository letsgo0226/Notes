#!/usr/bin/env python3
"""CLSDP: bounded epistemic-closure audit, NEVER a live-trading authorizer.

A finite checklist is useful for machine-verifiable completeness. Even a
perfect self-reported evidence package cannot authenticate its own origin.
Research cannot issue privileged grants to itself. No brokerage, secrets,
deployment, order routing or outbound network requests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

PROTOCOL = "HSI-CLSDP-REASONING-CLOSURE/1"
PROGRAM = 55067263
MAX_BYTES = 131072
STATUS_SET = frozenset(("PASS", "FAIL", "UNKNOWN"))
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
SYMBOL = "BTCUSDT"
QUOTE_CAP = "50"
DAILY_STOP = "2"
REQUIRED = {
    "market_data_integrity": "independent_market_data",
    "chronology_no_lookahead": "independent_backtest",
    "holdout_and_baseline_comparison": "independent_backtest",
    "cost_slippage_gap_stress": "independent_backtest",
    "exchange_filters_and_fee_assets": "independent_broker_audit",
    "complete_position_and_open_orders": "independent_broker_audit",
    "historical_cost_basis_and_transfers": "independent_broker_audit",
    "utc_daily_loss_latch": "independent_risk_audit",
    "restarts_duplicates_and_network_failure": "independent_risk_audit",
    "least_privilege_and_kill_switch": "independent_security_review",
    "immutable_reviewed_release": "independent_code_review",
    "operator_release_approval": "independent_human_approval",
}


class ClosureInputError(ValueError):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc(value):
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise ClosureInputError("INVALID_UTC_TIMESTAMP")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ClosureInputError("INVALID_UTC_TIMESTAMP") from exc


def evaluate(evidence, *, as_of=None):
    """Assess claimed completeness, not cryptographic provenance or permission.

    Self-declared issuer_class and sha256 cannot authenticate an issuer.
    Therefore ALL statuses remain untrusted; even all PASS leads only to a
    candidate package for independent, authorized inspection.
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if (not isinstance(as_of, datetime) or as_of.utcoffset() is None
            or as_of.utcoffset().total_seconds() != 0):
        raise ClosureInputError("UTC_CLOCK_REQUIRED")
    if not isinstance(evidence, dict) or evidence.get("protocol") != PROTOCOL:
        raise ClosureInputError("INVALID_EVIDENCE_PROTOCOL")
    policy = evidence.get("policy")
    if policy != {
        "symbol": SYMBOL, "max_order_quote_usdt": QUOTE_CAP,
        "utc_daily_realized_loss_stop_usdt": DAILY_STOP,
        "real_trading_enabled": False,
    }:
        raise ClosureInputError("RISK_POLICY_MISMATCH_OR_ENABLED")
    if evidence.get("program") != PROGRAM or type(evidence.get("program")) is not int:
        raise ClosureInputError("TM_PROGRAM_MISMATCH")
    rows = evidence.get("assertions")
    if not isinstance(rows, dict) or set(rows) != set(REQUIRED):
        raise ClosureInputError("MISSING_OR_UNKNOWN_GATES")
    statuses = {}
    issues = []
    counted = 0
    for gate, expected_issuer in REQUIRED.items():
        row = rows[gate]
        if not isinstance(row, dict) or set(row) != {
            "status", "issuer_class", "observation_utc", "evidence_sha256"
        }:
            raise ClosureInputError("MALFORMED_ASSERTION")
        status = row["status"]
        issuer = row["issuer_class"]
        digest = row["evidence_sha256"]
        if (type(status) is not str or status not in STATUS_SET
                or type(issuer) is not str or issuer != expected_issuer
                or type(digest) is not str or not SHA_RE.fullmatch(digest)):
            raise ClosureInputError("INVALID_ATTESTATION_CLAIM")
        obs = _utc(row["observation_utc"])
        delta = (as_of - obs).total_seconds()
        fresh = 0 <= delta <= 86400
        statuses[gate] = status if fresh else "UNKNOWN"
        if statuses[gate] == "PASS":
            counted += 1
        else:
            issues.append({"gate": gate, "reason":
                           "STALE_OR_FUTURE_EVIDENCE" if not fresh
                           else "CLAIM_" + status})
    all_claimed = counted == len(REQUIRED)
    return {
        "protocol": PROTOCOL, "program": PROGRAM, "symbol": SYMBOL,
        "status": ("SELF_ASSERTED_COMPLETE_NEEDS_INDEPENDENT_REVIEW"
                   if all_claimed else "REVIEW_BLOCKED"),
        "claimed_pass_count": counted,
        "required_count": len(REQUIRED),
        "claimed_statuses": statuses,
        "issues": issues,
        "evidence_sha256": hashlib.sha256(_canonical(evidence)).hexdigest(),
        "critical_limitations": [
            "JSON issuer labels and SHA256 digests are self-assertions, not signatures or trusted provenance",
            "A closed consistency loop cannot establish real-world trading profitability",
            "A fresh timestamp does not establish complete broker positions, cost basis or fee coverage",
            "A 2 USDT realized-loss stop cannot guarantee a 2 USDT maximum loss",
            "Formal F^2=I concerns a TM clock, not irreversible market prices or account balances",
            "Independent security review and specific release authorization remain external to this program",
        ],
        "source_authenticated_by_this_program": False,
        "broker_reconciled_by_this_program": False,
        "production_ready_by_this_program": False,
        "can_modify_deployment": False,
        "can_change_binance_permissions": False,
        "can_grant_order_permission": False,
        "live_order_permission": "DENIED",
        "live_release": "EXPLICIT_SEPARATE_HUMAN_ACTION_REQUIRED",
        "broker_calls": 0, "real_orders": 0,
    }


def inspect_file(path, *, as_of=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ClosureInputError("EVIDENCE_MISSING_LINKED_OR_OVERSIZE")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(
            ClosureInputError("NONFINITE_JSON_NUMBER")))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ClosureInputError("EVIDENCE_READ_FAILED") from exc
    return evaluate(data, as_of=as_of)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--as-of", help="UTC clock override for deterministic offline testing")
    args = parser.parse_args(argv)
    try:
        report = inspect_file(args.input, as_of=_utc(args.as_of) if args.as_of else None)
    except (ClosureInputError, TypeError, OverflowError) as exc:
        parser.exit(2, "CLSDP_REJECTED: " + str(exc) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "SELF_ASSERTED_COMPLETE_NEEDS_INDEPENDENT_REVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
