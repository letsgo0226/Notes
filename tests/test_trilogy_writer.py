"""Offline tests for structure, resume rules and safety controls."""
import copy
from pathlib import Path
import unittest
from unittest import mock
import tempfile
import os
import trilogy_writer as w


class TrilogyWriterTests(unittest.TestCase):
    def test_first_target(self):
        step = w.next_section(w.state_default())
        self.assertEqual(step[:3], (0, 0, 0))
        self.assertTrue(step[-1].as_posix().endswith("part_01.md"))

    def test_no_overwrite_and_state_advances(self):
        st = w.state_default()
        for i in range(w.PARTS_PER_CHAPTER):
            sec = w.next_section(st)
            st = w.advance(st, sec, sec[-1].relative_to(w.ROOT), 1200, "mock")
        self.assertEqual((st["book"], st["chapter"], st["part"]), (0, 1, 0))
        self.assertEqual(len(st["completed"]), w.PARTS_PER_CHAPTER)

    def test_finish_all_three_books(self):
        st = w.state_default()
        expected = sum(len(book[3]) for book in w.BOOKS) * w.PARTS_PER_CHAPTER
        for _ in range(expected):
            sec = w.next_section(st)
            st = w.advance(st, sec, sec[-1].relative_to(w.ROOT), 1400, "mock")
        self.assertIsNone(w.next_section(st))
        self.assertEqual(len(st["completed"]), expected)

    def test_mock_generation_then_daily_cap(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            destination = root / "books" / "reading-trilogy"
            with mock.patch.object(w, "ROOT", root), \
                 mock.patch.object(w, "OUTPUT", destination), \
                 mock.patch.object(w, "STATE_PATH", destination / "state.json"), \
                 mock.patch.object(w, "request_model", return_value=("哲" * 1400, "mock-model")), \
                 mock.patch.dict(os.environ, {"TRILOGY_ENABLED": "true"}):
                self.assertEqual(w.main(["--write"]), 0)
                self.assertTrue((destination / "state.json").exists())
                self.assertEqual(len(w.load_state()["completed"]), 1)
                self.assertEqual(w.main(["--write"]), 0)
                self.assertEqual(len(w.load_state()["completed"]), 1)

    def test_custom_url_requires_own_token(self):
        with mock.patch.dict(os.environ, {
            "WRITER_API_URL": "https://api.example.org/chat/completions",
            "GITHUB_TOKEN": "fake-github-token",
            "WRITER_API_KEY": "",
        }):
            with self.assertRaises(RuntimeError):
                w.request_model("test")

    def test_status_and_gating(self):
        self.assertEqual(w.main(["--plan"]), 0)
        self.assertEqual(w.PARTS_PER_CHAPTER, 8)
        self.assertGreater(w.MIN_HAN, 500)
        self.assertEqual(w.MAX_REQUESTS_PER_DAY, 1)


if __name__ == "__main__":
    unittest.main()
