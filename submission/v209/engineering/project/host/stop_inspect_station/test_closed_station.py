"""Explicit fake-backend workflow tests, never evidence of FPGA accuracy."""
from pathlib import Path
import tempfile,threading,unittest,json
from controller import sha
from closed_station import ClosedStation
from calibration import load,save

class FakeProfiles:
    def __init__(self):
        self.profile_id='texture';self.boot=123;self.fail=False;self.mapping={};self.frames=0
        self.block=threading.Event();self.block.set();self.started=threading.Event()
    def public_profiles(self):return [dict(id=x,name=x,note='fake fixture',model_sha256=x+'-model') for x in ['texture','roof']]
    def check(self):
        if self.fail:raise ConnectionError('Injected board failure')
        return dict(boot_identity=self.boot,model_sha256=self.profile_id+'-model',profile_id=self.profile_id)
    def activate(self,key):
        if key not in ['texture','roof']:raise ValueError('Unknown fixture profile')
        self.profile_id=key;return self.check()
    def inspect(self,image,folder):
        self.started.set()
        if not self.block.wait(3):raise TimeoutError('Injected inference timeout')
        self.check();self.frames+=1;folder.mkdir();raw=('fake-result-'+str(self.frames)).encode();(folder/'raw_result.bin').write_bytes(raw)
        return dict(pl_image_alarm=self.mapping[sha(image)],model_sha256=self.profile_id+'-model',
                    boot_identity=self.boot,pl_frame_sequence=self.frames,result_sha256=sha(folder/'raw_result.bin'))

class ClosedLoop(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.backend=FakeProfiles();rows=[]
        for i in range(6):
            p=self.root/f'{i}.fixture';p.write_bytes(('explicit fixture '+str(i)).encode());self.backend.mapping[sha(p)]=int(i>=4)
            rows.append(dict(id=str(i),file=str(p),sha256=sha(p),name='Fixture '+str(i),source_url='https://example.invalid',validation_scope='development_examples',qualified_model_sha256='texture-model'))
        self.station=ClosedStation(self.backend,rows,self.root/'records')
    def tearDown(self):
        self.backend.block.set()
        if self.station.worker:self.station.worker.join(5)
        self.temp.cleanup()
    def act(self,op,**values):
        s=self.station.state();return self.station.action(dict(op=op,session=s['session'],revision=s['revision'],operator='test operator',**values))
    def wait(self):
        if self.station.worker:self.station.worker.join(5);self.assertFalse(self.station.worker.is_alive())
        return self.station.state()
    def material(self,key='texture'):
        self.act('create_material',name='Fixture material '+key,profile_id=key,conditions='Fixture file replay, no physical camera')
        self.assertEqual(self.wait()['phase'],'READY')
    def capture(self,ident,purpose='inspection'):
        self.act('load',sample_id=str(ident),purpose=purpose,conditions_confirmed=True)
        self.act('inspect',input_held_confirmed=True);return self.wait()
    def review(self,verdict,note=''):
        return self.act('review',verdict=verdict,note=note,result_id=self.station.cycle['result']['id'])
    def dispose(self,op='segregate'):
        self.act(op,operator_confirmed=True,result_id=self.station.cycle['result']['id']);return self.wait()
    def check(self,i):
        purpose='calibration_defect' if i>=4 else 'calibration_good'
        self.capture(i,purpose);self.review('defect' if i>=4 else 'good');self.dispose()
    def calibrated(self):
        self.material()
        for i in [0,1,2,4]:self.check(i)
        self.act('freeze_calibration',conditions_confirmed=True);self.assertEqual(self.wait()['phase'],'READY')
    def test_missing_material_or_calibration_blocks_production(self):
        with self.assertRaises(ValueError):self.capture(0)
        self.material()
        with self.assertRaises(ValueError):self.capture(0)
        with self.assertRaises(ValueError):self.act('freeze_calibration',conditions_confirmed=True)
        self.assertEqual(self.station.phase,'READY')
    def test_three_unique_normals_and_defect_then_immutable_certificate(self):
        self.calibrated();run=self.station.calibrations.summary(self.station.run_id)
        self.assertEqual((run['normal_checks'],run['defect_checks']),(3,1));self.assertIsNotNone(run['certificate'])
        with self.assertRaises(ValueError):self.capture(3,'calibration_good')
    def test_duplicate_image_cannot_fill_calibration_count_or_both_roles(self):
        self.material();self.check(0)
        for purpose in ['calibration_good','calibration_defect']:
            with self.assertRaises(ValueError):self.capture(0,purpose)
    def test_mismatched_calibration_blocks_certificate_and_is_not_discarded(self):
        self.material();self.capture(4,'calibration_good');self.review('good','intentional wrong fixture declaration');self.dispose()
        for i in [0,1,2,5]:self.check(i)
        with self.assertRaises(ValueError):self.act('freeze_calibration',conditions_confirmed=True)
        self.assertEqual(self.station.calibrations.summary(self.station.run_id)['failed_checks'],1)
    def test_fpga_good_and_catalog_qualification_do_not_bypass_manual_review(self):
        self.calibrated();self.capture(0);self.assertEqual(self.station.phase,'REVIEW_HOLD')
        with self.assertRaises(ValueError):self.dispose('release')
        self.review('good');self.assertEqual(self.dispose('release')['phase'],'RELEASED')
        audit=self.station.audit()['records'][-1];self.assertEqual(audit['review'],'good');self.assertEqual(audit['disposition'],'release')
    def test_fpga_alarm_cannot_be_overridden_to_good_release(self):
        self.calibrated();self.capture(4);self.review('good','intentional reviewer error')
        self.assertEqual(self.station.phase,'CONFLICT_HOLD')
        with self.assertRaises(ValueError):self.dispose('release')
        self.assertEqual(self.dispose()['phase'],'REMOVED');self.assertTrue(self.station.calibrations.summary(self.station.run_id)['revoked'])
    def test_human_detected_miss_isolates_and_requires_reverification(self):
        self.calibrated();self.capture(0);self.review('defect','injected reviewer defect finding')
        self.assertEqual(self.dispose()['phase'],'SEGREGATED')
        with self.assertRaises(ValueError):self.capture(1)
    def test_uncertain_requires_reason_and_never_releases(self):
        self.calibrated();self.capture(0)
        with self.assertRaises(ValueError):self.review('uncertain')
        self.review('uncertain','Need another view')
        with self.assertRaises(ValueError):self.dispose('release')
        self.assertEqual(self.dispose()['phase'],'REMOVED')
    def test_stale_and_duplicate_review_rejected(self):
        self.calibrated();self.capture(0)
        with self.assertRaises(ValueError):self.act('review',verdict='good',result_id='old')
        self.review('good')
        with self.assertRaises(ValueError):self.review('defect','cannot overwrite')
    def test_cannot_switch_material_while_holding_or_inspecting(self):
        self.calibrated();material=self.station.material_id;self.act('load',sample_id='0',purpose='inspection',conditions_confirmed=True)
        with self.assertRaises(ValueError):self.act('select_material',material_id=material)
        self.backend.block.clear();self.act('inspect',input_held_confirmed=True);self.assertTrue(self.backend.started.wait(2))
        with self.assertRaises(ValueError):self.act('select_material',material_id=material)
        self.backend.block.set();self.wait()
    def test_conditions_confirmation_required_for_inspection(self):
        self.calibrated()
        with self.assertRaises(ValueError):self.act('load',sample_id='0',purpose='inspection')
    def test_board_loss_before_release_preserves_invalidated_review(self):
        self.calibrated();self.capture(0);self.review('good');self.backend.fail=True
        self.assertEqual(self.dispose('release')['phase'],'FAULT');self.assertIsNone(self.station.cycle['result'])
        self.assertEqual(self.station.cycle['invalidated_evidence'][0]['review']['verdict'],'good')
        self.assertEqual(self.station.counts['released'],0)
    def test_changed_raw_artifact_blocks_release_and_faults(self):
        self.calibrated();self.capture(0);self.review('good')
        (self.station.store/'cycles'/self.station.cycle['id']/'fpga/raw_result.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.dispose('release')
        self.assertEqual(self.station.phase,'FAULT');self.assertEqual(self.station.counts['released'],0)
    def test_new_run_invalidates_old_cycle_and_keeps_prior_certificate(self):
        self.calibrated();old_run=self.station.run_id;self.capture(0);self.review('good');self.dispose('release')
        self.act('restart_calibration',reason='Change conditions for another verification run');self.wait()
        self.assertNotEqual(old_run,self.station.run_id);self.assertIsNone(self.station.cycle)
        self.assertIsNotNone(self.station.calibrations.runs[old_run]['certificate'])
        with self.assertRaises(ValueError):self.capture(0)
    def test_new_session_keeps_certificates_but_never_restores_result(self):
        self.calibrated();material=self.station.material_id
        other=ClosedStation(self.backend,list(self.station.catalog.values()),self.station.store)
        self.assertIsNone(other.cycle);self.assertIsNone(other.material_id);self.assertIn(material,other.calibrations.materials)
    def test_new_boot_starts_fresh_calibration_instead_of_reusing_certificate(self):
        self.calibrated();old_run=self.station.run_id;self.backend.boot=124
        self.act('select_material',material_id=self.station.material_id);self.wait()
        self.assertNotEqual(old_run,self.station.run_id);self.assertIsNone(self.station.calibrations.summary(self.station.run_id)['certificate'])
    def test_tampered_certificate_cannot_authorize_production(self):
        self.calibrated();r=self.station.calibrations.runs[self.station.run_id]
        p=self.station.calibrations.root/self.station.material_id/'certificates'/(r['certificate']['id']+'.json')
        envelope=json.loads(p.read_text());envelope['record']['profile_sha256']='forged';p.write_text(json.dumps(envelope))
        with self.assertRaises(ValueError):self.capture(0)
    def test_browser_cannot_select_undeployed_profile(self):
        with self.assertRaises(ValueError):self.material('unknown')
        self.assertFalse(self.station.calibrations.materials)
    def test_calibration_samples_do_not_increment_production_release(self):
        self.material();self.check(0)
        self.assertEqual(self.station.counts['calibration_samples'],1);self.assertEqual(self.station.counts['released'],0)

if __name__=='__main__':unittest.main(verbosity=2)
