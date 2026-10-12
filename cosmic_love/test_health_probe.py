"""No-write canary operational probe tests."""
import json
from pathlib import Path
import tempfile
import unittest
from cosmic_love import closure_worker as w
from cosmic_love import health_probe as h

class ProbeTests(unittest.TestCase):
    def test_missing_journal_is_ready(self):
        with tempfile.TemporaryDirectory() as d:
            x=h.inspect(Path(d)/"missing.jsonl")
            self.assertEqual(x["status"],"READY_FOR_FINITE_STAGE")
            self.assertEqual(x["stages"],0)
            self.assertFalse(x["journal_exists"])
    def test_probing_does_not_change_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state.jsonl"
            w.advance(p,4)
            before=p.read_bytes()
            self.assertEqual(h.inspect(p,4)["stages"],1)
            self.assertEqual(before,p.read_bytes())
    def test_resource_limit_not_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state.jsonl"
            w.advance(p,2)
            self.assertEqual(h.inspect(p,2)["status"],"HOLD_RESOURCE_LIMIT")
    def test_corrupt_journal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state.jsonl"
            p.write_text('{"bad":true}\n')
            with self.assertRaises(ValueError):h.inspect(p)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state.jsonl";alias=Path(d)/"alias.jsonl"
            p.write_bytes(b'')
            alias.symlink_to(p)
            with self.assertRaises(ValueError):h.inspect(alias)
    def test_never_claims_deploy_or_trading(self):
        with tempfile.TemporaryDirectory() as d:
            x=h.inspect(Path(d)/"missing")
            self.assertFalse(x["self_deployment_enabled"])
            self.assertFalse(x["live_trading_authorized"])
if __name__=="__main__":unittest.main()
