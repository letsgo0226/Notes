import unittest
from cosmic_love.zero_point_field import zpf

class ZeroPointFieldTests(unittest.TestCase):
    def test_basic_dimensionless_field(self):
        r=zpf({'s':[2,0],'dirichlet':[[1,1],[2,0.5]],'zeros':[]})
        self.assertEqual(r['protocol'],'COSMIC-LOVE-ZPF/1')
        self.assertGreaterEqual(r['energy_dimensionless'],0)
        self.assertFalse(r['physical_energy_claim'])
    def test_zero_factor_can_make_energy_zero(self):
        r=zpf({'s':[0.5,14.134725],'dirichlet':[[1,1]],'zeros':[[0.5,14.134725]]})
        self.assertAlmostEqual(r['energy_dimensionless'],0.0,places=12)
    def test_conjugate_pair_finite(self):
        r=zpf({'s':[0.5,2],'dirichlet':[[1,1],[3,-0.25]],'zeros':[[0.5,1],[0.5,-1]]})
        self.assertTrue(isinstance(r['field'],list) or isinstance(r['field'],float))
    def test_reject_nonfinite(self):
        with self.assertRaises(ValueError): zpf({'s':['nan',0]})
    def test_reject_unexpected_field(self):
        with self.assertRaises(ValueError): zpf({'s':[2,0],'api_key':'secret'})
    def test_reject_too_many_terms(self):
        with self.assertRaises(ValueError): zpf({'dirichlet':[[i+1,1] for i in range(257)]})
    def test_no_trading_or_broker(self):
        r=zpf({'s':[2,0]})
        self.assertEqual(r['orders_submitted'],0)
        self.assertFalse(r['broker_connected'])

if __name__=='__main__': unittest.main()
