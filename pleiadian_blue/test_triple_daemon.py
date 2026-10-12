import json
import tempfile
import unittest
from pathlib import Path
from pleiadian_blue import daemon

class TestTripleDaemon(unittest.TestCase):
    def setUp(self):
        daemon.STOP=False
    def test_opt_in_crosskernel_and_resumption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            db=root/"state.sqlite3";status=root/"status.json"
            daemon.serve(db,status,None,0.01,3,triple_every=2,
                         triple_p=1829,triple_bits="1",triple_steps=8)
            a=json.loads(status.read_text())
            self.assertEqual(a["ticks"],3)
            self.assertEqual(a["triple_kernel"]["status"],"FINITE_VERIFIED")
            self.assertTrue(a["triple_kernel"]["triple_equivalent"])
            self.assertEqual(a["orders"],0)
            daemon.serve(db,status,None,0.01,2,triple_every=1)
            b=json.loads(status.read_text())
            self.assertEqual(b["ticks"],5)
            self.assertEqual(b["triple_kernel"]["status"],"FINITE_VERIFIED")
    def test_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            daemon.serve(root/"db",root/"status",None,0.01,1)
            self.assertNotIn("triple_kernel",json.loads((root/"status").read_text()))
    def test_reject_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):
                daemon.serve(root/"db",root/"status",None,1,1,triple_every=1,triple_bits="X")

if __name__=="__main__":unittest.main()
