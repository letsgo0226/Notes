"""Synthetic protocol tests, explicitly not evidence of live AI/source access."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
FOLDER = Path(__file__).resolve().parents[1] / "Notes" / "Dolphin_Logos_Riemann_Feedback"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load("dolphin", FOLDER / "dolphin_logos.py")
v = load("dolphin_verifier", FOLDER / "verify_feedback.py")


class Fixture:
    provider = "SYNTHETIC_TEST_FIXTURE"
    fixture = True

    def __init__(self, fail=None, echo=False):
        self.fail, self.echo, self.calls = fail, echo, []

    def preflight(self): pass

    def generate(self, phase, messages, schema):
        self.calls.append(phase)
        if phase == self.fail:
            raise RuntimeError("Injected model failure")
        data = json.loads(messages[1]["content"])
        count = len(data["recent_working_questions"]) if not self.echo else 0
        questions = [
            ["愛作為承諾如何接受相反的行為證據？", "誰有權決定合作的價值尺度？"],
            ["閱讀的陌生感會否改變對理性的要求？", "文字的聲韻如何影響理解的步驟？"],
            ["同一文本重訪時的記憶能否形成反證？", "詮釋差異是否意味對象已經改变？"],
            ["責任與自由在何種情境發生衝突？", "法則在歷史中應該怎樣重新理解？"]
        ][min(count, 3)]
        base = {"theme": "測試詮釋", "interpretation": "只把素材作為問題來源。",
                "questions": questions, "fact_checks": ["需要外部查證的測例命題。"]}
        if phase == "proposal":
            result = base
        elif phase == "critique":
            result = {"objections": [{"id": "a", "objection": "概念未定義。"},
                                      {"id": "b", "objection": "例子不能推出全稱結論。"}],
                      "counterexample": "相同讀者可能讀出不同結論。"}
        else:
            result = {**base, "change_from_previous": "增加可反駁的條件。",
                      "responses": [{"objection_id": "a", "response": "需工作定義。", "resolution": "open"},
                                    {"objection_id": "b", "response": "縮小主張範圍。", "resolution": "addressed"}]}
        return copy.deepcopy(result), {"provider": self.provider, "synthetic_fixture": True,
                                       "model": "NO_ACTUAL_MODEL"}


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.catalog = {"entries": [
            {"id": "oiSkrxINkHA", "channel_id": m.sources.CHANNEL, "title": "Fixture A",
             "url": "https://www.youtube.com/watch?v=oiSkrxINkHA"},
            {"id": "yr48-3M5nLU", "channel_id": m.sources.CHANNEL, "title": "Fixture B",
             "url": "https://www.youtube.com/watch?v=yr48-3M5nLU"}],
            "priority_ids": ["oiSkrxINkHA"]}
        self.reader = lambda x: m.sources.material_for(x, offline=True)

    def run_one(self, backend=None):
        return m.run_round(self.out, self.catalog, backend or Fixture(),
                           material_reader=self.reader, day="2026-10-12")

    def test_three_phases_and_independent_replay(self):
        backend = Fixture()
        row = self.run_one(backend)
        self.assertEqual(backend.calls, ["proposal", "critique", "revision"])
        self.assertEqual(row["verdict"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(v.verify(self.out)["synthetic_fixture_calls"], 3)
        self.assertEqual(v.verify(self.out)["real_local_model_calls"], 0)

    def test_failure_preserves_attempt_and_resumes_successful_phases(self):
        bad = Fixture(fail="critique")
        with self.assertRaisesRegex(RuntimeError, "Injected"):
            self.run_one(bad)
        state = m.load_state(self.out)
        self.assertEqual(state["calls_by_date"]["2026-10-12"], 2)
        self.assertFalse(state["rounds"])
        good = Fixture()
        self.run_one(good)
        self.assertEqual(good.calls, ["critique", "revision"])
        self.assertEqual(m.load_state(self.out)["calls_by_date"]["2026-10-12"], 4)
        v.verify(self.out)

    def test_source_drift_blocks_resume_without_new_call(self):
        with self.assertRaises(RuntimeError):
            self.run_one(Fixture(fail="critique"))
        self.catalog["entries"][0]["title"] = "Changed source"
        backend = Fixture()
        with self.assertRaisesRegex(ValueError, "Source changed"):
            self.run_one(backend)
        self.assertFalse(backend.calls)

    def test_revisits_material_and_carries_residual_history(self):
        a, b, c = self.run_one(), self.run_one(), self.run_one()
        self.assertNotEqual(a["source"]["id"], b["source"]["id"])
        self.assertEqual(a["source"]["id"], c["source"]["id"])
        self.assertEqual(c["visit"], 1)
        self.assertEqual(c["dirichlet"]["terms"], 3)
        v.verify(self.out)

    def test_echo_is_rejected(self):
        self.run_one(Fixture(echo=True))
        row = self.run_one(Fixture(echo=True))
        self.assertEqual(row["verdict"], "ECHO_REJECTED")
        with self.assertRaises(ValueError):
            m.review(self.out, row["id"], "approve", "Human note")

    def test_automatic_memory_stays_empty(self):
        self.run_one()
        state = m.load_state(self.out)
        self.assertEqual(m.memory_context(state, m.round_records(self.out, state)), [])

    def test_synthetic_fixture_cannot_be_approved(self):
        row = self.run_one()
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            m.review(self.out, row["id"], "approve", "Human note")

    def test_daily_budget_blocks_before_backend(self):
        for _ in range(4):
            self.run_one()
        backend = Fixture()
        with self.assertRaisesRegex(RuntimeError, "BUDGET"):
            self.run_one(backend)
        self.assertFalse(backend.calls)
        self.assertEqual(m.load_state(self.out)["calls_by_date"]["2026-10-12"], 12)

    def test_malformed_outputs_cannot_elevate_fact_status(self):
        with self.assertRaises(ValueError):
            m.validate({"verified": True}, m.PROPOSAL_SCHEMA)

    def test_missing_critique_binding_is_rejected(self):
        row = self.run_one()
        final = copy.deepcopy(row["final"])
        final["responses"][0]["objection_id"] = "fabricated"
        with self.assertRaises(ValueError):
            m.residual(final, row["phases"]["critique"]["output"], row["source"], [])

    def test_invalid_revision_resumes_only_revision(self):
        class BadRevision(Fixture):
            def generate(self, phase, messages, schema):
                result, metadata = super().generate(phase, messages, schema)
                if phase == "revision":
                    result["responses"][0]["objection_id"] = "wrong"
                return result, metadata
        with self.assertRaises(ValueError):
            self.run_one(BadRevision())
        self.assertNotIn("revision", m.load_state(self.out)["pending"]["phases"])
        good = Fixture()
        self.run_one(good)
        self.assertEqual(good.calls, ["revision"])
        self.assertEqual(m.load_state(self.out)["calls_by_date"]["2026-10-12"], 4)
        v.verify(self.out)

    def test_verifier_detects_tampered_output(self):
        self.run_one()
        path = self.out / m.load_state(self.out)["rounds"][0]
        row = json.loads(path.read_text())
        row["final"]["theme"] = "Tampered"
        m.write_json(path, row)
        with self.assertRaises(AssertionError):
            v.verify(self.out)

    def test_caption_content_does_not_enter_public_journal(self):
        self.run_one()
        row = json.loads((self.out / m.load_state(self.out)["rounds"][0]).read_text())
        self.assertNotIn("text", row["source"])
        self.assertNotIn("text", row["source"]["window"])
        self.assertEqual(row["source"]["modality"], "METADATA_ONLY")

    def test_local_provider_rejects_remote_and_cloud(self):
        for host in ("https://api.openai.com", "http://example.com", "http://localhost@evil.com"):
            with self.assertRaises(ValueError):
                m.Ollama(host=host)
        with self.assertRaises(ValueError):
            m.Ollama(model="qwen3:cloud")

    def test_concurrent_process_cannot_enter(self):
        with m.run_lock(self.out):
            with self.assertRaises(RuntimeError):
                with m.run_lock(self.out):
                    pass

    def test_catalog_channel_identity_is_bound(self):
        with self.assertRaises(ValueError):
            m.sources.normalize_catalog({"channel_id": "different", "entries": self.catalog["entries"]})

    def test_caption_json_and_vtt_parsing(self):
        raw = json.dumps({"events": [{"segs": [{"utf8": "Love &amp; care"}]}]}).encode()
        self.assertEqual(m.sources.caption_text(raw, "json3"), "Love & care")
        self.assertEqual(m.sources.caption_text(b"WEBVTT\n\n00:00.000 --> 00:01.000\n<i>Care</i>\n", "vtt"), "Care")

    def test_caption_urls_cannot_escape_to_other_hosts(self):
        self.assertFalse(m.sources.caption_url_allowed("https://evil.com/api/timedtext"))
        self.assertFalse(m.sources.caption_url_allowed("http://www.youtube.com/api/timedtext"))
        self.assertTrue(m.sources.caption_url_allowed("https://www.youtube.com/api/timedtext?v=abc"))

    def test_plan_performs_no_model_or_source_network(self):
        target = self.out / "plan-only"
        with patch.object(m.sources, "material_for", side_effect=AssertionError("Network")):
            self.assertEqual(m.main(["--plan", "--out", str(target)]), 0)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
