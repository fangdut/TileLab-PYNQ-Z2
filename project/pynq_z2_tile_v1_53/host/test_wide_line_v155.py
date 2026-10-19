from pathlib import Path
import sys,unittest
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from wide_line_reference_v155 import wide_line_score,mask_from_scores,detect
from directional_mean_reference import detect as old_detect

class WideLineTests(unittest.TestCase):
    def test_scalar_independent(self):
        a=np.random.default_rng(155).integers(0,256,(64,80),dtype=np.uint8);score=wide_line_score(a)
        for y,x in [(16,16),(25,31),(47,63),(35,51)]:
            best=0
            for dx,dy in [(1,0),(0,1),(1,1),(1,-1)]:
                values=[]
                for off in [0,-4,4]:
                    xx=x-dy*off;yy=y+dx*off
                    total=sum(int(a[yy+dy*k,xx+dx*k]) for k in range(-3,4))+int(a[yy,xx])
                    values.append(total//8)
                best=max(best,min(values[1:])-values[0])
            self.assertEqual(int(score[y,x]),best)
    def test_flat_step_and_overflow(self):
        for value in [0,255]:self.assertFalse(wide_line_score(np.full((64,80),value,np.uint8)).any())
        step=np.full((64,80),255,np.uint8);step[:,:40]=0
        self.assertFalse(wide_line_score(step).any())
        line=np.full((64,80),200,np.uint8);line[:,38:43]=40
        self.assertEqual(int(wide_line_score(line)[32,40]),160)
    def test_border_contract(self):
        a=np.random.default_rng(1).integers(0,256,(64,80),dtype=np.uint8);s=wide_line_score(a)
        self.assertFalse(s[:16].any() or s[-16:].any() or s[:,:16].any() or s[:,-16:].any())
        self.assertTrue(s[16:-16,16:-16].any())
    def test_no_new_strong_seeds(self):
        z=np.zeros((64,80),np.uint8);line=np.full_like(z,255);keep=np.ones_like(z,bool)
        self.assertFalse(mask_from_scores(z,z,z,z,line,keep,1).any())
    def test_disabled_exact_and_monotonic(self):
        rng=np.random.default_rng(155)
        for _ in range(4):
            rgb=rng.integers(0,256,(64,80,3),dtype=np.uint8)
            old=old_detect(rgb,roi=None);disabled=detect(rgb,28,enabled=False,roi=None);new=detect(rgb,28,roi=None)
            self.assertTrue(np.array_equal(old,disabled));self.assertFalse((old&~new).any())
    def test_roi_and_validation(self):
        rgb=np.random.default_rng(155).integers(0,256,(64,80,3),dtype=np.uint8);mask=detect(rgb,28,roi=(20,20,55,43))
        outside=np.ones(mask.shape,bool);outside[20:44,20:56]=False;self.assertFalse(mask[outside].any())
        for bad in [0,256,True,1.5]:
            with self.assertRaises(ValueError):detect(rgb,bad,roi=None)
if __name__=='__main__':unittest.main()
