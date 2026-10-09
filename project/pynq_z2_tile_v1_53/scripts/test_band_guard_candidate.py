from pathlib import Path
import hashlib,json,sys,unittest
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from band_guard_candidate import grow_band
from weak_reference import grow

class BandGuardTests(unittest.TestCase):
    def test_four_opposed_pairs_with_third_support_accept_very_weak_center(self):
        for pair in (((0,-1),(0,1)),((-1,0),(1,0)),((-1,-1),(1,1)),((-1,1),(1,-1))):
            m=np.zeros((9,9),bool);w=m.copy();v=m.copy();v[4,4]=True
            for y,x in pair:m[4+y,4+x]=True
            third=next(q for q in ((-1,0),(-1,1),(0,1),(1,1)) if q not in pair);m[4+third[0],4+third[1]]=True
            self.assertTrue(grow_band(m,w,v)[4,4]);self.assertFalse(grow(m,w,3)[4,4])
    def test_opposed_pair_alone_is_not_enough_for_new_band(self):
        m=np.zeros((9,9),bool);m[4,3]=m[4,5]=True;w=np.zeros_like(m);v=w.copy();v[4,4]=True
        self.assertFalse(grow_band(m,w,v)[4,4])
    def test_one_sided_three_support_rejected_only_in_very_weak_band(self):
        m=np.zeros((9,9),bool);m[3,3:6]=True;w=np.zeros_like(m);v=w.copy();v[4,4]=True
        self.assertFalse(grow_band(m,w,v)[4,4]);w[4,4]=True;self.assertTrue(grow_band(m,w,v)[4,4])
    def test_unseeded_and_outside_both_bands_not_promoted(self):
        m=np.zeros((9,9),bool);v=np.ones_like(m);w=m.copy();self.assertFalse(grow_band(m,w,v).any())
        m[3,3:6]=True;m[5,4]=True;self.assertFalse(grow_band(m,w,w)[4,4])
    def test_random_superset_of_baseline_and_subset_of_unrestricted_lower_band(self):
        rng=np.random.default_rng(150)
        for _ in range(32):
            score=rng.integers(0,256,(37,43));v=score>34;w=score>45;seed=score>90;a=seed.copy();b=seed.copy();c=seed.copy();reach=seed.copy()
            for step in range(4):
                a=grow(a,w,3);b=grow_band(b,w,v);c=grow(c,v,3);reach=grow(reach,np.ones_like(v),1)
                self.assertFalse(np.any(a&~b));self.assertFalse(np.any(b&~c));self.assertFalse(np.any(b&~v));self.assertFalse(np.any(b&~reach));self.assertFalse(np.any(seed&~b))
    def test_border_has_no_wraparound(self):
        m=np.zeros((7,7),bool);m[2:5,6]=True;w=np.zeros_like(m);v=np.ones_like(m)
        self.assertFalse(grow_band(m,w,v)[3,0])
    def test_invalid_inputs_rejected(self):
        m=np.zeros((3,3),bool)
        with self.assertRaises(ValueError):grow_band(m,m,np.zeros((2,2),bool))
        with self.assertRaises(ValueError):grow_band(m,m,m.astype(np.uint8))

if __name__=='__main__':
    out=R/'reports/v150';out.mkdir(parents=True,exist_ok=True)
    with (out/'candidate_unit.log').open('w',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BandGuardTests))
    result=dict(passed=r.wasSuccessful(),tests=r.testsRun,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),R/'models/band_guard_candidate.py',R/'models/weak_reference.py')})
    (out/'candidate_unit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=result['passed'],tests=result['tests'])));sys.exit(not result['passed'])
