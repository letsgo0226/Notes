"""Sparse QTM algebra, supplied CLI, payload compatibility and bounded --run tests."""
import contextlib
import importlib.util
import io
import itertools
import json
from pathlib import Path
import random
import shlex
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'hsi_cosmic_quantum.py'
if not PATH.exists(): PATH=ROOT/'engine/hsi_cosmic_quantum.py'
if PATH.exists():
    spec=importlib.util.spec_from_file_location('quantum_under_test',PATH)
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
else:
    import types
    q=types.SimpleNamespace()
    with contextlib.redirect_stdout(io.StringIO()):
        exec(shlex.split((ROOT/'lfp_atgc_tm_2kb.sh').read_text())[3], q.__dict__)
SHELL=ROOT/('hsi_qtm_2kb.sh' if PATH.exists() else 'lfp_atgc_tm_2kb.sh')

class QuantumTests(unittest.TestCase):
    def test_supplied_superposition_phases_and_exact_support(self):
        psi={(0,0,()):1/q.sqrt(2),(1,0,()):1j/q.sqrt(2)}
        expected={(1,1,()):1j/q.sqrt(2),(0,-1,()):1/q.sqrt(2)}
        self.assertTrue(q.eq(q.U(psi),expected))
        self.assertTrue(q.eq(q.U(expected),psi))

    def test_all_finite_basis_samples_keep_tape_and_recur(self):
        for bits in itertools.product((0,1),repeat=4):
            tape=tuple(i-2 for i,b in enumerate(bits) if b)
            for state in (0,1):
                for head in range(-3,4):
                    psi={(state,head,tape):1}
                    target=(1-state,head+1-2*state,tape)
                    self.assertEqual(q.U(psi),{target:1j if state==0 else -1j})
                    self.assertTrue(q.eq(q.U(q.U(psi)),psi))

    def test_complex_superposition_preserves_norm_and_inner_product(self):
        rng=random.Random(42)
        keys=[(s,h,t) for s in (0,1) for h in range(-3,4) for t in ((),(-1,0,2))]
        x={k:complex(rng.uniform(-1,1),rng.uniform(-1,1)) for k in keys}
        y={k:complex(rng.uniform(-1,1),rng.uniform(-1,1)) for k in keys}
        inner=lambda a,b:sum(v.conjugate()*b.get(k,0) for k,v in a.items())
        self.assertAlmostEqual(q.norm(q.U(x)),q.norm(x),places=10)
        self.assertAlmostEqual(abs(inner(q.U(x),q.U(y))-inner(x,y)),0,places=10)
        self.assertTrue(q.eq(q.U(q.U(x)),x))

    def test_declared_sparse_cutoff_is_not_claimed_exact_for_tiny_terms(self):
        self.assertEqual(q.U({(0,0,()):1e-13}),{})

    def test_cli_is_one_line_under_2kb_and_matches_certificate(self):
        text=SHELL.read_bytes()
        self.assertEqual(len(text.splitlines()),1);self.assertLess(len(text),2048)
        p=subprocess.run(['sh',str(SHELL)],capture_output=True,text=True,timeout=5,check=True)
        cert=json.loads(p.stdout)
        self.assertEqual(cert['protocol'],'HSI-COSMIC-QUANTUM-SELF-CLOSURE/QTM-1.0')
        self.assertTrue(all(cert[k] for k in ('transition_verified','norm_preserved','U2_identity')))
        if PATH.exists(): self.assertEqual(cert,q.certificate())
        payload=ROOT/'payload/lfp_atgc_tm_2kb.sh'
        if payload.exists():self.assertEqual(payload.read_bytes(),text)

    def test_run_really_continues_and_can_be_stopped_by_host(self):
        process=subprocess.Popen(['sh',str(SHELL),'--run'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            with self.assertRaises(subprocess.TimeoutExpired):process.communicate(timeout=.2)
        finally:
            process.terminate();out,err=process.communicate(timeout=5)
        self.assertTrue(json.loads(out)['two_step_quantum_recurrence'])
        self.assertEqual(err,'')

if __name__=='__main__':unittest.main()
