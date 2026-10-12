"""Offline regression and bounded HSI TM integration tests: no AI credentials."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import trilogy_tm_corpus as m

class TMWriterTests(unittest.TestCase):
    def test_locked_sixteen_sources(self):
        lock, inv=m.inventory()
        self.assertEqual(len(inv["observed"]),16)
        self.assertEqual(inv["inventory_status"],"SOURCE_INVENTORY_VERIFIED")
        self.assertEqual(lock["source_repo"],"letsgo0226/Notes")
    def test_real_tm_checkpoint(self):
        rows,state,choice=m.machine("10101010")
        self.assertEqual(len(rows),16)
        self.assertEqual(state["n"],16)
        rows2,state2,choice2=m.machine("10101010",state)
        self.assertEqual(len(rows2),16)
        self.assertEqual(state2["n"],32)
        self.assertNotEqual(rows[0]["step"],rows2[0]["step"])
        self.assertNotEqual(choice,choice2)
    def test_offline_writer_persists_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/"book-output"
            one=m.build(offline=True,output=target)
            self.assertEqual(one["model_calls"],0)
            self.assertEqual(one["web_research"]["status"],"OFFLINE")
            first_state=m.load_state(target)
            self.assertEqual(len(first_state["completed"]),1)
            dossier=(target/first_state["completed"][0]["folder"]/
                     "dossier.md").read_text(encoding="utf-8")
            self.assertIn("全部 16 個檔案",dossier)
            self.assertIn("全部 16 份來源",dossier)
            two=m.build(offline=True,output=target)
            self.assertNotEqual((one["book"],one["chapter"]),(two["book"],two["chapter"]))
            self.assertEqual(len(m.load_state(target)["completed"]),2)
            self.assertEqual(m.load_state(target)["tm_checkpoint"]["n"],32)
    def test_all_sixteen_files_have_content_profiles(self):
        _, inv=m.inventory()
        rows=m.source_profiles(inv)
        self.assertEqual(len(rows),16)
        self.assertEqual({x["file"] for x in rows},set(inv["observed"]))
        self.assertTrue(all(x["bytes"]>0 and x["line_count"]>0 for x in rows))
        self.assertTrue(all(x["summarization"]=="MECHANICAL_KEYWORD_COUNTS_NOT_SEMANTIC_ANALYSIS" for x in rows))

    def test_crossref_rejects_unrelated_subjects(self):
        payload={"message":{"items":[
            {"DOI":"10.1234/patent","title":["Patent infringement limitation"]},
            {"DOI":"10.1234/ethics","title":["Ethics of care and love"]}
        ]}}
        def fetch(req,timeout):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        found=m.crossref_metadata("ethics of care love",fetcher=fetch)
        self.assertEqual(found["status"],"FOUND")
        self.assertEqual([x["doi"] for x in found["records"]],["10.1234/ethics"])

    def test_crossref_metadata_only(self):
        payload={"message":{"items":[{"DOI":"10.1234/example","title":["A Test of Reason"],
            "author":[{"given":"A","family":"Scholar"}],
            "published":{"date-parts":[[2024,5]]},"type":"journal-article"}]}}
        def fetch(req,timeout):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        record=m.crossref_metadata("reason",fetcher=fetch)
        self.assertEqual(record["status"],"FOUND")
        self.assertEqual(len(record["records"]),1)
        self.assertEqual(record["records"][0]["year"],2024)
        self.assertNotIn("abstract",record["records"][0])
    def test_offline_makes_no_network_request(self):
        def forbidden(*args,**kwargs): raise AssertionError("Network accessed in offline mode")
        self.assertEqual(m.crossref_metadata("love",offline=True,fetcher=forbidden)["status"],"OFFLINE")
    def test_work_budget(self):
        self.assertEqual(len(m.chapters()),25)
        self.assertEqual(m.TM_LIMIT,16)
        self.assertEqual(m.TM_BUDGET,12)

if __name__=="__main__":
    unittest.main()
