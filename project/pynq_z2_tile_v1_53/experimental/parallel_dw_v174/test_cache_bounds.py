"""Reject buffer overflow geometries before FPGA implementation/programming."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/fpga_texture_v170'))
from check_direct_cache import analyze

def task(ic=48,iw=28,k=1,stride=1,depth=False):
    t=[0]*24;t[0]=2 if depth else 1
    t[7:14]=[iw,iw,ic,48,k,stride,0]
    return t

class CacheBounds(unittest.TestCase):
    def test_real_batch_capacity_and_odd_tail(self):
        for banked in (False,True):
            for width in (7,13,14,27,28,55,56,111,112,224):
                r=analyze([task(ic=144,iw=width)],banked)[0]
                self.assertEqual(r['output_rows_covered'],width)
                self.assertLess(r['max_cache_word'],8192)
    def test_cache_overflow_is_rejected(self):
        for banked in (False,True):
            with self.assertRaisesRegex(ValueError,'storage'):
                analyze([task(ic=8192,iw=224)],banked)
    def test_banked_uncached_shape_guard(self):
        analyze([task(ic=48,stride=2)])
        with self.assertRaisesRegex(ValueError,'physical row banks'):
            analyze([task(ic=49,stride=2)])
    def test_flat_uncached_storage_guard(self):
        analyze([task(ic=96,iw=224,stride=2)],banked=False)
        with self.assertRaisesRegex(ValueError,'flat line storage'):
            analyze([task(ic=160,iw=224,stride=2)],banked=False)
    def test_quant_row_overflow_guard(self):
        for banked in (False,True):
            with self.assertRaisesRegex(ValueError,'geometry'):
                analyze([task(iw=225)],banked)

if __name__=='__main__':unittest.main()
