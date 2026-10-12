import os
import unittest
from unittest.mock import patch
from hsi_cosmic_zero_field import build_zero_field

TM={'enabled':True,'verified':True,'program':55067263,'control_uid':'fixture',
    'transition_table':[{'q':q,'a':a,'next_q':1-q,'write':a,'direction':1-2*q} for q in (0,1) for a in (0,1)]}

class ZeroFieldTests(unittest.TestCase):
    def test_default_prime_spectrum_and_zeros(self):
        c=build_zero_field(TM,9)
        self.assertEqual('prime',c['dirichlet_basis'])
        self.assertEqual([8.0,14.0,21.0],[z['imaginary'] for z in c['inserted_zeros']])
        self.assertTrue(all(c['checks'].values()))
        self.assertEqual(9,len(c['events']))
    def test_deterministic_bounded_modulation(self):
        a,b=build_zero_field(TM,11),build_zero_field(TM,11)
        self.assertEqual(a,b)
        self.assertGreater(len({x['rate_delta'] for x in a['events']}),2)
        self.assertTrue(all(0<=x['unit_energy']<=1 for x in a['events']))
    def test_alternating_basis_and_changed_zeros(self):
        with patch.dict(os.environ,{'HSI_ZERO_FIELD_BASIS':'alternating','HSI_ZERO_FIELD_ZEROS':'0.5:14'}):
            c=build_zero_field(TM,9)
        self.assertEqual('alternating',c['dirichlet_basis'])
        self.assertTrue(all(c['checks'].values()))
        self.assertEqual(0.0,c['events'][4]['energy'])
    def test_reject_modified_tm(self):
        with self.assertRaises(ValueError):build_zero_field(dict(TM,program=17),9)
    def test_disabled(self):
        with patch.dict(os.environ,{'HSI_ZERO_FIELD':'0'}):self.assertFalse(build_zero_field(TM,9)['enabled'])
        self.assertFalse(build_zero_field({'enabled':False},9)['enabled'])
    def test_invalid_configuration(self):
        for cfg in [{'HSI_ZERO_FIELD_AMPLITUDE':'nan'}, {'HSI_ZERO_FIELD_ZEROS':'bad'}, {'HSI_ZERO_FIELD_TERMS':'9'}, {'HSI_ZERO_FIELD_BASIS':'bogus'}]:
            with patch.dict(os.environ,cfg):
                with self.assertRaises(ValueError):build_zero_field(TM,9)
    def test_scope(self):
        self.assertIn('no physical vacuum energy',build_zero_field(TM,9)['epistemic_scope'])

if __name__=='__main__':unittest.main()
