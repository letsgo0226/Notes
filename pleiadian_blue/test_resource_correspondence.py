import unittest
from pleiadian_blue.resource_correspondence import sample

class TestResourceCorrespondence(unittest.TestCase):
    def test_measurement_and_semantic_stability(self):
        a=sample(1829,"1",8)
        b=sample(1829,"1",8)
        self.assertTrue(a["semantic_result"]["triple_equivalent"])
        self.assertEqual(a["semantic_sha256"],b["semantic_sha256"])
        for key in ("wall_ns","process_cpu_ns","peak_process_rss_bytes"):
            self.assertGreaterEqual(a["measurement"][key],0)
    def test_reject_bad_parameters(self):
        for p,bits,steps in [(-1,"1",1),(1,"2",1),(1,"1",257)]:
            with self.assertRaises(ValueError):sample(p,bits,steps)

if __name__=="__main__":unittest.main()
