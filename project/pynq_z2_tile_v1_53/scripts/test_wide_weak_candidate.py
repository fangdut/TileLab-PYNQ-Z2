from pathlib import Path
import hashlib,json,sys,unittest
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from weak_reference import grow
from wide_weak_candidate import wide_weak_mask

class WideWeakTests(unittest.TestCase):
    def test_wide_response_cannot_create_seeds(self):
        n=np.zeros((20,20),int);w=np.full_like(n,200)
        self.assertFalse(wide_weak_mask(n,w,np.ones_like(n,bool)).any())
    def test_connected_wide_weak_addition(self):
        n=np.zeros((20,20),int);w=n.copy();n[8,8:11]=100;w[9,9]=60
        m=wide_weak_mask(n,w,np.ones_like(n,bool))
        self.assertTrue(m[9,9]);self.assertEqual(m.sum(),4)
    def test_strict_thresholds_and_roi(self):
        n=np.zeros((20,20),int);w=n.copy();n[8,8:11]=100;w[9,9]=45
        roi=np.ones_like(n,bool)
        self.assertFalse(wide_weak_mask(n,w,roi)[9,9]);w[9,9]=46
        self.assertTrue(wide_weak_mask(n,w,roi)[9,9]);roi[9,9]=False
        self.assertFalse(wide_weak_mask(n,w,roi)[9,9])
    def test_superset_bounded_growth_and_seed_preservation(self):
        rng=np.random.default_rng(152)
        for _ in range(32):
            n=rng.integers(0,120,(25,30));w=rng.integers(0,150,n.shape);roi=rng.random(n.shape)>.1
            b=(n>90)&roi;s=b.copy();reach=b.copy()
            for _ in range(4):b=grow(b,(n>45)&roi,3);reach=grow(reach,roi,1)
            m=wide_weak_mask(n,w,roi)
            self.assertFalse((b&~m).any());self.assertFalse((s&~m).any());self.assertFalse((m&~reach).any())
    def test_wide_ridge_geometry(self):
        g=np.full((100,100),180);g[:,40:61]=100
        n=valley(g,8);w=valley(g,16)
        self.assertEqual(n[50,50],0);self.assertEqual(w[50,50],80)
        self.assertEqual(w[0,50],0);self.assertEqual(w[50,0],0)
    def test_invalid_shape(self):
        a=np.zeros((20,20),int)
        for args in ((a,a[:2],a>0),(a,a,a)):
            with self.assertRaises(ValueError):wide_weak_mask(*args)

if __name__=='__main__':
    out=R/'reports/v152';out.mkdir(parents=True,exist_ok=True)
    with (out/'candidate_unit.log').open('x',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WideWeakTests))
    result=dict(passed=r.wasSuccessful(),tests=r.testsRun,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),R/'models/wide_weak_candidate.py',R/'models/weak_reference.py',R/'models/valley_reference.py')})
    (out/'candidate_unit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=result['passed'],tests=result['tests'])));sys.exit(not result['passed'])
