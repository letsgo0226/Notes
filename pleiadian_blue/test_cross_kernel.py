import unittest
from pleiadian_blue.cross_kernel import compare, sweep, bitset_to_bytes, bytes_to_bitset

class TestCrossKernel(unittest.TestCase):
    def test_negative_tape_coordinates(self):
        s={-17,-9,-8,-1,0,7,8,17}
        self.assertEqual(bytes_to_bitset(bitset_to_bytes(s)),s)
    def test_default_st_machine(self):
        r=compare(1829,"1",8)
        self.assertEqual(r["status"],"HALTED")
        self.assertEqual(r["steps_verified"],1)
    def test_finite_sweep(self):
        r=sweep()
        self.assertEqual(r["cases"],660)
        self.assertEqual(r["result"],"FINITE_CASES_PASSED")

if __name__=="__main__":unittest.main()
