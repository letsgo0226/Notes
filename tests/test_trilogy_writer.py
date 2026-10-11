"""Offline tests for structure, resume rules and safety controls."""
import copy
from pathlib import Path
import unittest
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

    def test_status_and_gating(self):
        self.assertEqual(w.main(["--plan"]), 0)
        self.assertEqual(w.PARTS_PER_CHAPTER, 8)
        self.assertGreater(w.MIN_HAN, 500)
        self.assertEqual(w.MAX_REQUESTS_PER_DAY, 1)


if __name__ == "__main__":
    unittest.main()
