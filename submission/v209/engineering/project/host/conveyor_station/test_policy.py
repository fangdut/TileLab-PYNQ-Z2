# SPDX-License-Identifier: MIT
import copy,sys,threading,unittest,os
from pathlib import Path
SOURCE=Path(os.environ.get('TILELAB_STATION_SOURCE',Path(__file__).resolve().parents[1]/'stop_inspect_station'))
sys.path.insert(0,str(SOURCE))
from policy_station import PolicyStation
sys.path.remove(str(SOURCE))


class Harness(PolicyStation):
    def __init__(self):
        self.lock=threading.RLock();self.session='test';self.revision=1;self.phase='REVIEW_HOLD'
        self.cycle=dict(id='tile',purpose='inspection',review=None,
            result=dict(id='result',pl_image_alarm=0,result_sha256='sha'))
        self.counts=dict(automatic_passed=0,released=0,manual_reviews=0)
        self.store=Path('.');self.events=[];self.stop_requested=True;self.valid=True
        self.backend=type('Backend',(),{'check':lambda _:dict(boot_identity=1,model_sha256='model')})()
    def _cycle_context(self,certificate=False):
        if not self.valid:raise ValueError('certificate revoked')
        return dict(boot_identity=1,profile_sha256='model')
    def _check_review_artifacts(self):pass
    def _artifacts(self):pass
    def _event(self,name,**fields):self.events.append(dict(name=name,**fields))
    def _launch(self,task):task()
    def _save_cycle(self,folder):self.saved=copy.deepcopy(self.cycle)
    def state(self):return dict(phase=self.phase,cycle=self.cycle)
    def _fault(self,error):self.phase='FAULT'


class PolicyTests(unittest.TestCase):
    def body(self):return dict(session='test',revision=1,op='automatic_release',policy_id='FPGA_NO_ALARM_AUTO_PASS_V207',result_id='result')
    def test_auto_pass_never_fabricates_human_review(self):
        s=Harness();s.action(self.body())
        self.assertEqual(s.phase,'RELEASED')
        self.assertIsNone(s.cycle['review'])
        self.assertEqual(s.counts['manual_reviews'],0)
        self.assertEqual(s.counts['automatic_passed'],1)
        self.assertIsNone(s.cycle['disposition']['review_id'])
    def test_alarm_never_auto_passes(self):
        s=Harness();s.cycle['result']['pl_image_alarm']=1
        with self.assertRaises(ValueError):s.action(self.body())
        self.assertEqual(s.phase,'REVIEW_HOLD')
    def test_stale_result_is_rejected(self):
        s=Harness();b=self.body();b['result_id']='old'
        with self.assertRaises(ValueError):s.action(b)
    def test_invalid_certificate_is_rejected(self):
        s=Harness();s.valid=False
        with self.assertRaises(ValueError):s.action(self.body())
    def test_existing_human_review_cannot_be_overwritten(self):
        s=Harness();s.cycle['review']={'verdict':'defect'}
        with self.assertRaises(ValueError):s.action(self.body())


if __name__=='__main__':unittest.main()
