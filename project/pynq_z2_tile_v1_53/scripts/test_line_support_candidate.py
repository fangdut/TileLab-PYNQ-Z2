"""Geometry and bounded-growth invariants for the offline candidate."""
from pathlib import Path
import hashlib,json,sys,unittest
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from line_support_candidate import grow_line
from weak_reference import grow

class LineSupportTests(unittest.TestCase):
    def test_four_opposed_orientations_extend_weak_line(self):
        for dy,dx in ((0,1),(1,0),(1,1),(1,-1)):
            m=np.zeros((9,9),bool);w=m.copy()
            for k in (-1,0,1):w[4+k*dy,4+k*dx]=True
            m[4-dy,4-dx]=True
            self.assertTrue(grow_line(m,w)[4,4]);self.assertFalse(grow(m,w,3)[4,4])
    def test_one_sided_weak_step_and_unseeded_line_are_not_promoted(self):
        m=np.zeros((9,9),bool);w=m.copy();w[4,3:5]=True;m[4,3]=True
        self.assertFalse(grow_line(m,w)[4,4]);m[:]=False;w[4,5]=True;self.assertFalse(grow_line(m,w).any())
    def test_dense_weak_patch_with_only_one_seed_keeps_original_mask(self):
        m=np.zeros((9,9),bool);m[4,3]=True;w=np.ones_like(m)
        self.assertTrue(np.array_equal(grow_line(m,w),m))
    def test_original_three_support_rule_is_preserved(self):
        m=np.zeros((9,9),bool);m[3,3:6]=True;w=np.ones_like(m)
        self.assertTrue(grow_line(m,w)[4,4]);self.assertTrue(np.all(~grow(m,w,3)|grow_line(m,w)))
    def test_four_stages_preserve_seeds_and_do_not_exceed_four_pixel_reach(self):
        w=np.zeros((31,31),bool);w[15,2:29]=True;m=np.zeros_like(w);m[15,15]=True
        for _ in range(4):m=grow_line(m,w)
        self.assertEqual(list(np.flatnonzero(m[15])),list(range(11,20)))
    def test_no_wraparound_at_image_border(self):
        m=np.zeros((7,7),bool);w=m.copy();m[3,6]=True;w[3,[0,1,6]]=True
        self.assertFalse(grow_line(m,w)[3,0])
    def test_random_monotonic_superset_and_candidate_containment(self):
        rng=np.random.default_rng(149)
        for _ in range(32):
            w=rng.random((37,43))<.4;seed=w&(rng.random(w.shape)<.3);a=seed.copy();b=seed.copy();reach=seed.copy()
            for stage in range(4):
                a=grow(a,w,3);b=grow_line(b,w);reach=grow(reach,np.ones_like(w),1)
                self.assertFalse(np.any(a&~b));self.assertFalse(np.any(b&~w));self.assertFalse(np.any(seed&~b));self.assertFalse(np.any(b&~reach))
    def test_invalid_inputs_are_rejected(self):
        for m,w in [(np.zeros((2,2),np.uint8),np.zeros((2,2),bool)),(np.zeros((2,2),bool),np.zeros((3,2),bool))]:
            with self.assertRaises(ValueError):grow_line(m,w)

if __name__=='__main__':
    out=R/'reports/v149';out.mkdir(parents=True,exist_ok=True)
    with (out/'candidate_unit.log').open('w',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LineSupportTests))
    value=dict(passed=result.wasSuccessful(),tests=result.testsRun,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),R/'models/line_support_candidate.py',R/'models/weak_reference.py')})
    (out/'candidate_unit.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(passed=value['passed'],tests=value['tests'])));sys.exit(not value['passed'])
