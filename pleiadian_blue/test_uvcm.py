import json
import tempfile
import unittest
from pathlib import Path
from pleiadian_blue import uvcm

SPEC={"start":"q0","halt":"HALT","transitions":{"q0:0":[1,1,"HALT"],"q0:1":[0,-1,"HALT"]}}
LOOP={"start":"q0","halt":"HALT","transitions":{"q0:0":[1,1,"q0"],"q0:1":[0,-1,"q0"]}}
class TestUVCM(unittest.TestCase):
    def test_single_step(self):
        s,status=uvcm.advance(SPEC,uvcm.initial(SPEC),1)
        self.assertEqual(status,"HALTED")
        self.assertEqual(s["ones"],[0])
    def test_split_equals_monolithic(self):
        first,status=uvcm.advance(LOOP,uvcm.initial(LOOP),11)
        resumed,status=uvcm.advance(LOOP,first,13)
        full,_=uvcm.advance(LOOP,uvcm.initial(LOOP),24)
        self.assertEqual(resumed,full)
        self.assertEqual(uvcm.encode257(resumed),uvcm.encode257(full))
    def test_checkpoint_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"state.json"
            state=uvcm.initial(SPEC)
            uvcm.save(path,SPEC,state,"UNRESOLVED_BUDGET")
            self.assertEqual(uvcm.load(path)["state"],state)
            wrapped=json.loads(path.read_text())
            wrapped["payload"]["state"]["h"]=42
            path.write_text(json.dumps(wrapped))
            with self.assertRaises(AssertionError):
                uvcm.load(path)
    def test_no_false_halting(self):
        s,status=uvcm.advance(LOOP,uvcm.initial(LOOP),4)
        self.assertEqual(status,"UNRESOLVED_BUDGET")
        self.assertEqual(uvcm.certificate(uvcm.initial(LOOP),s,4,status)["dirichlet_energy"],0)
if __name__=="__main__":unittest.main()
