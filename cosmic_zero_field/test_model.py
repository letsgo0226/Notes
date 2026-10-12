import math
import unittest
from cosmic_zero_field.model import Config,Field,P,machine,primes
from cosmic_zero_field.worker import main

class MathTests(unittest.TestCase):
    def test_encoded_seed(self):
        self.assertEqual(P,55067263)
        self.assertEqual(len(machine()),4)
    def test_two_step_cycle_all_symbol_pairs(self):
        rules={(q,a):(r,b,d) for q,a,r,b,d in machine()}
        for q in (0,1):
            for a in (0,1):
                for b in (0,1):
                    tape={0:a,1-2*q:b};old=tape.copy();h=0;st=q
                    for _ in range(2):
                        st,tape[h],direction=rules[st,tape[h]]
                        h+=direction
                    self.assertEqual((st,h,tape),(q,0,old))
    def test_prime_sequence(self):
        self.assertEqual(primes(8),(2,3,5,7,11,13,17,19))
    def test_zeros_both_signs_in_both_modes(self):
        for basis in ('prime','eta'):
            for n in (8,32,128):
                f=Field(Config(basis=basis,terms=n))
                for u,v in f.cfg.zeros:
                    for sign in (-1,1):
                        z=complex(u,sign*v)
                        val,_,energy=f.evaluate(z)
                        self.assertEqual(val,0j)
                        self.assertEqual(energy,0)
    def test_normalizer_positive(self):
        for basis in ('prime','eta'):
            for n in (8,16,32,64,128):
                self.assertGreater(Field(Config(basis=basis,terms=n)).anchor,0)
    def test_conjugation(self):
        f=Field()
        z=.31+5.43j
        a,_,energy_a=f.evaluate(z)
        b,_,energy_b=f.evaluate(z.conjugate())
        self.assertAlmostEqual(a.real,b.real,places=8)
        self.assertAlmostEqual(a.imag,-b.imag,places=8)
        self.assertAlmostEqual(energy_a,energy_b,places=8)
    def test_derivative_vs_central_difference(self):
        f=Field();z=.47+8.2j;eps=1e-5
        _,d,_=f.evaluate(z)
        forward=f.evaluate(z+eps)[0]
        backward=f.evaluate(z-eps)[0]
        finite=(forward-backward)/(2*eps)
        self.assertLess(abs(d-finite),1e-6*max(1,abs(d)))
    def test_analytic_polynomial_real_double_zero(self):
        f=Field(Config(zeros=((1.0,0.0),)))
        val,d,e=f.evaluate(1+0j)
        self.assertEqual((val,d,e),(0j,0j,0.0))
    def test_finite_energy(self):
        for basis in ('prime','eta'):
            f=Field(Config(basis=basis))
            for z in (-3+65j,0+0j,3+21j,1+40j):
                self.assertGreaterEqual(f.evaluate(z)[2],0)
    def test_config_reject_duplicate(self):
        with self.assertRaises(ValueError):Config(zeros=((0.5,8),(0.5,8)))
    def test_config_reject_nonfinite(self):
        with self.assertRaises(ValueError):Config(amplitude=float('nan'))
    def test_config_reject_large_n(self):
        with self.assertRaises(ValueError):Config(terms=1000000)
    def test_bounds(self):
        with self.assertRaises(ValueError):Field().evaluate(100+0j)
    def test_no_authority(self):
        result=Field().report()
        self.assertFalse(result['physical_energy_claim'])
        self.assertFalse(result['live_trading_authorized'])
        self.assertFalse(result['chat_access_authorized'])
        self.assertFalse(result['zeta_zeros_claim'])
    def test_worker_single_cycle(self):
        self.assertEqual(main(['--once']),0)

if __name__=='__main__':unittest.main()
