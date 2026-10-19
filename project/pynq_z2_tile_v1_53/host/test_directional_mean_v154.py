"""Numerical contract tests for the offline oracle, not live host detection."""
from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models'))
from directional_mean_reference import directional_mean_score,detect
from valley_reference import valley
from wide_weak_candidate import wide_weak_mask

class DirectionalMeanTests(unittest.TestCase):
    def test_random_pixels_match_scalar_equations(self):
        a=np.random.default_rng(3154).integers(0,256,(48,64),dtype=np.uint8)
        for r in (8,16):
            actual=directional_mean_score(a,r);half=r//2-1;off=r//4;div=r
            for y,x in ((r,r),(24,32),(47-r,63-r)):
                def avg(cx,cy,tx,ty):
                    return (sum(int(a[cy+ty*k,cx+tx*k]) for k in range(-half,half+1))+int(a[cy,cx]))//div
                expected=0
                for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
                    c=avg(x,y,dx,dy)
                    left=avg(x-off*dy,y+off*dx,dx,dy)
                    right=avg(x+off*dy,y-off*dx,dx,dy)
                    expected=max(expected,min(left,right)-c)
                self.assertEqual(int(actual[y,x]),expected)
            self.assertFalse(actual[:r].any());self.assertFalse(actual[-r:].any())
            self.assertFalse(actual[:,:r].any());self.assertFalse(actual[:,-r:].any())
    def test_no_response_on_flat_or_one_sided_step(self):
        for level in (0,100,255):
            a=np.full((64,80),level,dtype=np.uint8)
            for r in (8,16):self.assertFalse(directional_mean_score(a,r).any())
        a=np.zeros((64,80),dtype=np.uint8);a[:,40:]=255
        for r in (8,16):self.assertFalse(directional_mean_score(a,r).any())
    def test_disabled_mode_retains_accepted_baseline(self):
        rgb=np.random.default_rng(654).integers(0,256,(64,80,3),dtype=np.uint8)
        a=rgb.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
        keep=np.zeros(gray.shape,bool);keep[8:56,8:72]=True
        expected=wide_weak_mask(valley(gray,8),valley(gray,16),keep)
        np.testing.assert_array_equal(detect(rgb,roi=(8,8,71,55),enabled=False),expected)
    def test_intensity_overflow_and_thin_dark_ridge(self):
        a=np.full((64,80),255,dtype=np.uint8);a[:,39:42]=150
        for r in (8,16):
            s=directional_mean_score(a,r)
            self.assertEqual(s.dtype,np.uint8)
            self.assertGreater(int(s[32,40]),40)
    def test_reject_bad_inputs(self):
        with self.assertRaises(ValueError):directional_mean_score(np.zeros((8,8)),8)
        with self.assertRaises(ValueError):directional_mean_score(np.full((64,80),256),8)
        with self.assertRaises(ValueError):directional_mean_score(np.zeros((64,80)),4)
if __name__=='__main__':unittest.main()
