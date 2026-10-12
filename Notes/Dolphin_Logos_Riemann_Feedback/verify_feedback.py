#!/usr/bin/env python3
"""Independent offline journal replay; no inference or source network calls."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify(folder):
    folder = Path(folder)
    state = json.loads((folder / "state.json").read_text("utf-8"))
    assert state["protocol"] == "DOLPHIN-LOGOS-DIRICHLET/1", "state protocol"
    values, seen, fixtures, real_calls = [], set(), 0, 0
    for number, path in enumerate(state["rounds"], 1):
        assert re.fullmatch(r"rounds/[0-9]{6}-[a-f0-9]{16}\.json", path), "journal path"
        row = json.loads((folder / path).read_text("utf-8"))
        assert row["number"] == number and row["id"] not in seen, "journal order"
        seen.add(row["id"])
        raw = canonical(row["final"])
        assert hashlib.sha256(raw).hexdigest() == row["final_sha256"], "final digest"
        n, decoded = int(row["e257_hex"], 16), bytearray()
        assert n >= 1, "E257 sentinel"
        while n != 1:
            n, digit = divmod(n, 257)
            assert 1 <= digit <= 256, "E257 digit"
            decoded.append(digit - 1)
        assert bytes(reversed(decoded)) == raw, "independent E257 decode"
        assert set(row["phases"]) == {"proposal", "critique", "revision"}, "three phases"
        for phase, record in row["phases"].items():
            assert hashlib.sha256(canonical(record["output"])).hexdigest() == record["output_sha256"], phase
            bound = [a for a in state["attempts"] if a["round_id"] == row["id"] and a["phase"] == phase
                     and a["status"] == "STRUCTURE_VALIDATED"]
            assert any(a["request_sha256"] == record["request_sha256"] for a in bound), "request binding"
            if record["metadata"]["synthetic_fixture"]:
                fixtures += 1
            else:
                assert record["metadata"]["provider"] == "LOCAL_OLLAMA", "local inference provenance"
                assert record["metadata"].get("model_digest"), "local model digest"
                real_calls += 1
        assert row["final"] == row["phases"]["revision"]["output"], "revision binding"
        ids = [o["id"] for o in row["phases"]["critique"]["output"]["objections"]]
        answers = row["final"]["responses"]
        assert len(set(ids)) == len(ids), "unique objections"
        assert sorted(ids) == sorted(x["objection_id"] for x in answers), "critique coverage"
        assert row["epistemic_layers"]["external_facts"] == "UNVERIFIED", "fact status"
        assert not any(row["claims"].values()) and not row["approved_memory_added"], "claim ceiling"
        assert row["source"]["watched_video"] is False and row["source"]["listened_audio"] is False, "modality"
        assert "text" not in row["source"] and "text" not in row["source"]["window"], "no transcript publication"
        vector = row["residual_vector"]
        assert vector["missing_primary_content"] == float(row["source"]["modality"] not in (
            "PUBLISHED_CAPTION", "AUTO_CAPTION", "USER_PROVIDED_TEXT"))
        assert abs(sum(vector.values()) / len(vector) - row["residual_scalar"]) < 1e-12
        values.append(row["residual_scalar"])
        assert row["dirichlet"]["terms"] == number, "history length"
        for sample in row["dirichlet"]["samples"].values():
            s = complex(sample["s_real"], sample["s_imaginary"])
            total = sum(value / (n ** s) for n, value in enumerate(values, 1))
            assert abs(complex(sample["real"], sample["imaginary"]) - total) < 1e-10, "Dirichlet recomputation"
    for day, count in state["calls_by_date"].items():
        assert type(count) is int and 0 <= count <= 12, "daily budget"
        assert count == sum(x["date"] == day for x in state["attempts"]), "attempt ledger"
    return {"status": "FINITE_JOURNAL_REPLAY_VERIFIED", "rounds": len(values),
            "real_local_model_calls": real_calls, "synthetic_fixture_calls": fixtures,
            "approved_memory_entries": len({r["round_id"] for r in state["reviews"] if r["decision"] == "approve"}),
            "source_modality_verified": True, "semantic_truth_verified": False,
            "riemann_hypothesis_proven": False}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder", type=Path)
    args = cli.parse_args()
    try:
        print(json.dumps(verify(args.folder), sort_keys=True))
        return 0
    except (AssertionError, ValueError, KeyError, OSError) as exc:
        print(json.dumps({"status": "REPLAY_FAILED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
