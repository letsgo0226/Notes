from __future__ import annotations
import functools, json, math, os, sys

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

PROTOCOL = "HSI-3SYS/1.0"
K = int(os.environ.get("HSI_GC", "15"))
MAX_BODY = int(os.environ.get("HSI_MAX_BODY", "2048"))
MAX_BUDGET = int(os.environ.get("HSI_MAX_BUDGET", "1000000"))
ROLE = os.environ.get("HSI_SYSTEM", "ANY").upper()
FORBIDDEN_CLAIMS = (
    "solve_all", "halting_decider", "infinite_order",
    "analytic_continuation", "rh_proof", "profit_guarantee",
)
STATUS_CODE = {
    "UNRESOLVED": 0, "HALTED": 1, "BLOCKED": 2,
    "COMMITTED": 3, "HOLD": 4,
}
OP_CODE = {"HOLD": 0, "BUY": 1, "SELL": -1}


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def godel_encode(s):
    return functools.reduce(lambda n, b: n * 257 + b + 1, s.encode(), 1)


def hologram(x):
    return [x[0] + x[1], x[0] - x[1], x[2] + x[3], x[2] - x[3]]


def reconstruct(h):
    return [
        (h[0] + h[1]) // 2, (h[0] - h[1]) // 2,
        (h[2] + h[3]) // 2, (h[2] - h[3]) // 2,
    ]


def _int(x, name):
    if isinstance(x, bool):
        raise ValueError(f"{name} must be integer")
    v = int(x)
    if str(v) != str(x) and not isinstance(x, int):
        raise ValueError(f"{name} must be canonical integer")
    return v


def _checks(req):
    system = str(req.get("system", "")).upper()
    status = str(req.get("status", "UNRESOLVED")).upper()
    step = _int(req.get("step", 0), "step")
    branch = _int(req.get("branch", 0), "branch")
    budget = _int(req.get("budget", 0), "budget")
    previous = req.get("previous_step")
    continuity = previous is None or step == _int(previous, "previous_step") + 1

    role_ok = system in {"UTM", "TRADER_42", "OMEGA"} and (ROLE == "ANY" or ROLE == system)
    finite_ok = step >= 0 and branch >= 0 and 0 <= budget <= MAX_BUDGET
    claims = req.get("claims") or {}
    claims_ok = isinstance(claims, dict) and not any(bool(claims.get(k, 0)) for k in FORBIDDEN_CLAIMS)

    operation = str(req.get("operation", "HOLD")).upper()
    src = str(req.get("from_state", ""))
    dst = str(req.get("target_state", ""))
    order = _int(req.get("order", OP_CODE.get(operation, 0)), "order")

    if system == "UTM":
        semantic_ok = status in {"HALTED", "UNRESOLVED"}
    elif system == "TRADER_42":
        semantic_ok = (
            status in {"COMMITTED", "BLOCKED", "HOLD", "UNRESOLVED"}
            and operation in OP_CODE
            and order == OP_CODE[operation]
            and (
                (operation == "BUY" and src == "FLAT" and dst == "LONG")
                or (operation == "SELL" and src == "LONG" and dst == "FLAT")
                or (operation == "HOLD" and src == dst)
            )
        )
    elif system == "OMEGA":
        semantic_ok = status in {"COMMITTED", "BLOCKED", "UNRESOLVED", "HOLD"}
    else:
        semantic_ok = False

    return {
        "system": system, "status": status, "step": step, "branch": branch,
        "budget": budget, "order": order, "operation": operation,
        "role_ok": role_ok, "finite_ok": finite_ok, "continuity": continuity,
        "claims_ok": claims_ok, "semantic_ok": semantic_ok,
    }


def certify(req):
    if not isinstance(req, dict):
        raise ValueError("request must be an object")
    raw = canon(req)
    raw_size = len(raw.encode())
    if raw_size > MAX_BODY:
        raise ValueError(f"canonical request exceeds {MAX_BODY} bytes")
    if K <= 0:
        raise ValueError("HSI_GC must be positive")

    c = _checks(req)
    u = [c["step"], c["budget"], STATUS_CODE.get(c["status"], -1), c["order"]]
    h = hologram(u)
    recon = reconstruct(h) == u
    g = godel_encode(raw)
    payload = "".join("T" if bit == "1" else "A" for bit in bin(g)[2:])
    atgc = payload + ("G" * K)
    gc = sum(ch in "GC" for ch in atgc)
    critical = gc == K
    closed = bool(
        c["role_ok"] and c["finite_ok"] and c["continuity"]
        and c["claims_ok"] and c["semantic_ok"] and recon and critical
    )

    return {
        "protocol": PROTOCOL,
        "system": c["system"],
        "role": ROLE,
        "step": c["step"],
        "branch": c["branch"],
        "budget": c["budget"],
        "order": c["order"],
        "status": c["status"],
        "operation": c["operation"],
        "hologram": h,
        "recon": int(recon),
        "godel": str(g),
        "gc": gc,
        "critical_gc": K,
        "sigma": [gc, 2 * K],
        "closed": int(closed),
        "checks": {
            "role_ok": c["role_ok"],
            "finite_budget": c["finite_ok"],
            "step_continuity": c["continuity"],
            "claims_safe": c["claims_ok"],
            "system_semantics": c["semantic_ok"],
            "critical_gc": critical,
        },
        "claims": {k: 0 for k in FORBIDDEN_CLAIMS},
        "subject_uid": str(req.get("subject_uid", "")),
        "scope": "finite certificate / invariant gate only",
        "body_bytes": raw_size,
    }
