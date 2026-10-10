"""End-to-end continuous original dovetail + existing compressed HSI-CL-XY tests."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parent
RUN=BASE/"hsi_stream.py"
MICRO=BASE/"hsi_cl_xy_2k.sh"


def pair(n):
    w=(math.isqrt(8*n+1)-1)//2
    a=n-w*(w+1)//2
    return a,w-a+1


def original_sim(n,word="1"):
    r,T=pair(n)
    e,m=pair(r)
    p=e+1
    z=(math.isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    B=4*(k+1)
    q=h=0
    tape={i for i,x in enumerate(word) if x=="1"}
    steps=0
    for _ in range(T):
        if q==k:
            break
        digit=(c//pow(B,2*q+int(h in tape)))%B
        qq=digit%(k+1)
        digit//=k+1
        direction=digit%2
        digit//=2
        value=digit%2
        (tape.add(h) if value else tape.discard(h))
        h+=1 if direction else -1
        q=qq
        steps+=1
    return {"step":n,"branch":e,"budget":T,"order":m,"program":p,
            "status":"HALTED" if q==k else "UNRESOLVED",
            "xy_steps":steps,"q":q,"head":h,"tape_ones":len(tape)}


class Stream(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)/"stream.json"

    def run_stream(self, *args, state=None, expect=0, word="1"):
        env=dict(os.environ)
        for key in ("HSI_STATE","HSI_RULE","HSI_CAND","HSI_PERM"):
            env.pop(key,None)
        cmd=[sys.executable,str(RUN),"--state",str(state or self.state),
             "--microkernel",str(MICRO),"--sleep","0","--word",word,*args]
        r=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=60)
        self.assertEqual(r.returncode,expect,r.stderr)
        return [json.loads(x) for x in r.stdout.splitlines()]

    def test_original_dovetail_equivalence_and_resume(self):
        first=self.run_stream("--limit","5")
        second=self.run_stream("--limit","5")
        all_rows=first+second
        self.assertEqual(len(all_rows),10)
        for n,row in enumerate(all_rows):
            expected=original_sim(n)
            for key,val in expected.items():
                self.assertEqual(row[key],val,(n,key))
            self.assertEqual(row["xy_D0"],0)
            self.assertEqual(row["xy_D1_num"],0)
            self.assertEqual(row["xy_closed"],1)
            self.assertTrue(row["x"].isdigit() and row["y"].isdigit())
        self.assertEqual(json.loads(self.state.read_text())["next"],10)
        full=self.run_stream("--limit","10",state=Path(self.tmp.name)/"fresh.json")
        self.assertEqual(all_rows,full)

    def test_original_codes_are_xy_analytic_coordinates(self):
        from fractions import Fraction
        from hsi_stream import decode_e257
        rows=self.run_stream("--limit","9")
        seen=set()
        for n,row in enumerate(rows):
            r,T=pair(n)
            e,m=pair(r)
            self.assertEqual(decode_e257(row["x"]),[n,e,T,m,"1"])
            self.assertNotIn(row["x"],seen)
            seen.add(row["x"])
            g=int(row["y"])
            normalized=Fraction(g,g+1)
            self.assertGreater(normalized,0)
            self.assertLess(normalized,1)
            p,q,h,tape=decode_e257(row["y"])
            self.assertEqual(p,row["program"])
            self.assertEqual(q,row["q"])
            self.assertEqual(h,row["head"])
            self.assertEqual(len(tape),row["tape_ones"])
            self.assertEqual(row["analytic_sample"],"y/(1+y)")

    def test_bounded_skips_are_explicit_and_resumable(self):
        rows=self.run_stream("--limit","8","--max-budget","1")
        self.assertEqual(len(rows),8)
        self.assertTrue(any(x["status"]=="SKIPPED_BUDGET" for x in rows))
        for row in rows:
            if row["status"]=="SKIPPED_BUDGET":
                self.assertGreater(row["budget"],1)
                self.assertEqual(row["xy_closed"],0)
            else:
                self.assertEqual(row["xy_closed"],1)
        self.assertEqual(json.loads(self.state.read_text())["next"],8)

    def test_inner_xy_events_and_persistent_newline_output(self):
        rows=self.run_stream("--limit","2","--emit-xy")
        outer=[x for x in rows if x.get("protocol")=="HSI-UTM-XY-STREAM/1.0"]
        inner=[x for x in rows if "xy" in x]
        self.assertEqual(len(outer),2)
        self.assertTrue(inner)
        self.assertTrue(all(x["xy"]["protocol"]=="HSI-CL-XY/2K" for x in inner))

    def test_rejected_evolution_holds_without_skipping(self):
        self.run_stream("--limit","1","--evolve-rule","0",expect=3)
        d=json.loads(self.state.read_text())
        self.assertEqual(d["next"],0)
        self.run_stream("--limit","1","--evolve-rule","0",expect=3)
        self.assertEqual(json.loads(self.state.read_text())["next"],0)

    def test_resume_does_not_change_word(self):
        self.run_stream("--limit","1")
        self.run_stream("--limit","1",word="0",expect=3)
        self.assertEqual(json.loads(self.state.read_text())["next"],1)


if __name__=="__main__":
    unittest.main()
