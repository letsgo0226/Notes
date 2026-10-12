import os
import unittest
from unittest.mock import patch
from hsi_cosmic_zero_field import build_zero_field

TM = {'enabled': True, 'verified': True, 'program': 55067263, 'control_uid': 'fixture',
      'transition_table': [{'q':q,'a':a,'next_q':1-q,'write':a,'direction':1-2*q}
                           for q in (0,1) for a in (0,1)]}

class ZeroFieldTests(unittest.TestCase):
    def test_zeros_normalization_and_nonnegative_energy(self):
        a = build_zero_field(TM, 9)
        self.assertTrue(a['verified'])
        self.assertTrue(all(a['checks'].values()))
        self.assertEqual(0.0, a['events'][4]['energy'])
        self.assertTrue(all(0 <= x['unit_energy'] <= 1 for x in a['events']))
    def test_determinism_and_variation(self):
        a, b = build_zero_field(TM, 11), build_zero_field(TM, 11)
        self.assertEqual(a, b)
        self.assertGreater(len({x['rate_delta'] for x in a['events']}), 2)
    def test_reject_altered_tm(self):
        bad = dict(TM, program=17)
        with self.assertRaises(ValueError): build_zero_field(bad, 9)
    def test_disable(self):
        with patch.dict(os.environ, {'HSI_ZERO_FIELD': '0'}):
            self.assertFalse(build_zero_field(TM, 9)['enabled'])
    def test_bad_configuration(self):
        with patch.dict(os.environ, {'HSI_ZERO_FIELD_GAMMA': 'nan'}):
            with self.assertRaises(ValueError): build_zero_field(TM, 9)
        with patch.dict(os.environ, {'HSI_ZERO_FIELD_TERMS': '10000'}):
            with self.assertRaises(ValueError): build_zero_field(TM, 9)
    def test_non_ai_model_invariant(self):
        self.assertIn('no physical zero-point energy', build_zero_field(TM, 3)['epistemic_scope'])

if __name__ == '__main__': unittest.main()
