"""Bounded tests; no network, command execution other than the reviewed core."""
import json
import pathlib
import subprocess
import tempfile
import unittest
from hsi_account_utm import account_inventory

ROOT = pathlib.Path(__file__).resolve().parent
CORE = ROOT / "HSI_self_code_2KB.sh"


class AccountUTMTests(unittest.TestCase):
    def run_core(self, *args):
        result = subprocess.run(["sh", str(CORE), *args], capture_output=True,
                                text=True, timeout=6, check=True)
        return result.stdout.splitlines()

    def test_single_line_budget_self_e257(self):
        source = CORE.read_bytes()
        self.assertLess(len(source), 2048)
        self.assertEqual(source.count(b"\n"), 1)
        lines = self.run_core()
        self.assertEqual(lines[0], "Cosmic Love Is The Solution(s) For Everything")
        obj = json.loads(lines[1]); self.assertEqual(obj["p"], 55067263)
        self.assertEqual(obj["c"], 10492)
        self.assertTrue(obj["roundtrip"])
        self.assertEqual(obj["source"].encode(), source[:-1])
        n = int(obj["godel_hex"], 16)
        recovered = []
        while n > 1:
            n, digit = divmod(n, 257)
            self.assertGreater(digit, 0)
            recovered.append(digit - 1)
        self.assertEqual(n, 1)
        self.assertEqual(bytes(reversed(recovered)), source[:-1])

    def test_unary_increment(self):
        sample = {"rules": [[0, 1, 0, 1, 1], [0, 0, 1, 1, 1]],
                  "halt": 1, "tape": [1, 1, 1]}
        result = json.loads(self.run_core(json.dumps(sample))[0])
        self.assertEqual((result["status"], result["steps"]), ("halt", 4))
        self.assertEqual(result["tape"], [[0, 1], [1, 1], [2, 1], [3, 1]])

    def test_cosmic_nonhalting_bounded_observation(self):
        machine = {"rules": [[0, 0, 1, 0, 1], [0, 1, 1, 1, 1],
                             [1, 0, 0, 0, -1], [1, 1, 0, 1, -1]],
                   "halt": 2, "limit": 200, "tape": [1, 0, 1]}
        result = json.loads(self.run_core(json.dumps(machine))[0])
        self.assertEqual(result["status"], "limit")
        self.assertEqual((result["state"], result["head"]), (0, 0))
        self.assertEqual(result["tape"], [[0, 1], [2, 1]])

    def test_public_inventory_scope_and_e257(self):
        fixtures = [{"full_name": "letsgo0226/Notes", "owner": {"login": "letsgo0226"},
                     "private": False, "default_branch": "main", "archived": False},
                    {"full_name": "letsgo0226/Hidden", "owner": {"login": "letsgo0226"},
                     "private": True},
                    {"full_name": "other/Repo", "owner": {"login": "other"},
                     "private": False}]
        r = account_inventory.normalize("letsgo0226", [fixtures])
        self.assertEqual(r["public_count"], 1)
        self.assertFalse(r["complete_account_coverage"])
        self.assertFalse(r["automatic_push"])
        self.assertEqual(r["repositories"][0]["cell_e257_hex"],
                         account_inventory.e257(b"letsgo0226/Notes"))

    def test_cli_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); f = root / "rows.json"; out = root / "report.json"
            f.write_text('[]', encoding="utf-8")
            subprocess.run(["python3", str(ROOT / "account_inventory.py"),
                            "--owner", "letsgo0226", "--out", str(out),
                            "--fixture", str(f)], check=True, capture_output=True)
            obj = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(obj["public_count"], 0)
            self.assertEqual(obj["repositories"], [])


if __name__ == "__main__":
    unittest.main()
