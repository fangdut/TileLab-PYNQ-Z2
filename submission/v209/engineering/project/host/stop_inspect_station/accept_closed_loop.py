"""Physical FPGA closed-loop replay; API review actors are explicitly automated.

Uses exposed photo labels to exercise controls. It does not assert real human
review, independent accuracy, physical camera calibration or motor actuation.
"""
from pathlib import Path
import argparse,json,time,urllib.request,urllib.error,hashlib,sys

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--url',default='http://127.0.0.1:8793');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    expected=json.loads(a.expected.read_text());guards=[];cycles=[];certificates=[];actor='自动验收脚本（照片回放，非真实人工）'
    def request(path,body=None):
        req=urllib.request.Request(a.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
    def act(op,**values):
        s=request('/api/state');return request('/api/action',dict(op=op,session=s['session'],revision=s['revision'],operator=actor,**values))
    def wait():
        end=time.monotonic()+40
        while time.monotonic()<end:
            s=request('/api/state')
            if s['phase'] not in ['CONFIGURING','INSPECTING','CONFIRMING']:return s
            time.sleep(.04)
        raise TimeoutError('Closed-loop worker deadline')
    def reject(op,**values):
        try:act(op,**values)
        except urllib.error.HTTPError as error:
            assert error.code==409;guards.append(dict(op=op,error=json.load(error)['error']));(a.out/'guards.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2),encoding='utf8');return
        raise AssertionError('Unsafe action accepted: '+op)
    state=request('/api/state');assert state['closed_loop']['enabled'] and state['phase']=='READY' and not state['closed_loop']['materials']
    choices={}
    for profile in ['texture','roof']:
        good=sorted(k for k,v in expected.items() if v['profile_id']==profile and v['expected_alarm']==0)
        defect=sorted(k for k,v in expected.items() if v['profile_id']==profile and v['expected_alarm']==1)
        assert len(good)>=3 and len(defect)>=2
        choices[profile]=dict(good=good[:3],defect=defect[0],production_good=good[-1],production_defect=defect[1])
    (a.out/'plan.json').write_text(json.dumps(dict(scope='PHYSICAL_CONTROL_WORKFLOW_REPLAY_NOT_ACCURACY',selected_before_inference=choices,actor=actor,real_human_review=False,physical_actuation=False),ensure_ascii=False,indent=2),encoding='utf8')
    def capture(sample,purpose):
        act('load',sample_id=sample,purpose=purpose,conditions_confirmed=True)
        act('inspect',input_held_confirmed=True);s=wait();assert s['phase'] in ['CALIBRATION_HOLD','REVIEW_HOLD'],s
        c=s['cycle'];r=c['result'];truth=expected[sample]
        assert r['pl_image_alarm']==truth['expected_alarm'] and not r['cpu_detection'] and not r['gpu_detection']
        assert c['context']['profile_id']==truth['profile_id'] and r['model_sha256']==c['context']['profile_sha256']
        cycles.append(dict(sample_id=sample,purpose=purpose,cycle=c));(a.out/'cycles.json').write_text(json.dumps(cycles,ensure_ascii=False,indent=2),encoding='utf8')
        return s
    def review(s,verdict=None,note='公开标签驱动的API流程回放，不代表真实人员复核'):
        value=verdict or ('defect' if s['cycle']['result']['pl_image_alarm'] else 'good')
        return act('review',result_id=s['cycle']['result']['id'],verdict=value,note=note)
    def dispose(op):
        s=request('/api/state');act(op,operator_confirmed=True,result_id=s['cycle']['result']['id']);return wait()
    def calibration(profile):
        for sample in choices[profile]['good']+[choices[profile]['defect']]:
            purpose='calibration_good' if expected[sample]['expected_alarm']==0 else 'calibration_defect'
            s=capture(sample,purpose);reject('release',operator_confirmed=True,result_id=s['cycle']['result']['id'])
            review(s);assert dispose('segregate')['phase']=='REMOVED'
        reject('load',sample_id=choices[profile]['good'][0],purpose='calibration_defect')
        act('freeze_calibration',conditions_confirmed=True);s=wait();assert s['phase']=='READY' and s['closed_loop']['calibrated'] and s['cycle'] is None,s
        certificates.append(s['closed_loop']['run']['certificate'])
    materials={}
    for profile in ['texture','roof']:
        reject('create_material',name='invalid',profile_id='undeployed',conditions='file replay')
        act('create_material',name=('纹理砖' if profile=='texture' else '陶瓦')+'闭环验收',profile_id=profile,conditions='公开实拍照片回放；没有实体相机或光照标定')
        s=wait();assert s['phase']=='READY';materials[profile]=s['closed_loop']['active_material']['id']
        reject('freeze_calibration',conditions_confirmed=True)
        reject('load',sample_id=choices[profile]['production_good'],purpose='inspection',conditions_confirmed=True)
        calibration(profile)
        s=capture(choices[profile]['production_good'],'inspection');result=s['cycle']['result']['id']
        reject('release',operator_confirmed=True,result_id=result)
        reject('select_material',material_id=materials[profile])
        reject('review',result_id='stale',verdict='good')
        s=review(s);reject('review',result_id=result,verdict='good')
        reject('release',operator_confirmed=True,result_id='stale');assert dispose('release')['phase']=='RELEASED'
        s=capture(choices[profile]['production_defect'],'inspection');review(s);assert dispose('segregate')['phase']=='SEGREGATED'
    act('select_material',material_id=materials['texture']);s=wait();assert s['closed_loop']['calibrated'] and s['cycle'] is None
    s=capture(choices['texture']['production_defect'],'inspection');s=review(s,'good','故障注入：模拟错误人工判断，真实标签仍为缺陷')
    assert s['phase']=='CONFLICT_HOLD' and not s['closed_loop']['calibrated']
    reject('release',operator_confirmed=True,result_id=s['cycle']['result']['id']);assert dispose('segregate')['phase']=='REMOVED'
    reject('load',sample_id=choices['texture']['production_good'],purpose='inspection',conditions_confirmed=True)
    act('restart_calibration',reason='自动验收：模拟复核冲突后重新核验，保留旧批次');assert wait()['phase']=='READY';calibration('texture')
    # A real externally changed reference must invalidate a held good result.
    s=capture(choices['texture']['production_good'],'inspection');review(s)
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/fpga_texture_v170'))
    from board_client import Board
    Board(timeout=15).upload(a.profiles/'roof')
    assert dispose('release')['phase']=='FAULT'
    act('reset_fault',operator_confirmed=True)
    act('restart_calibration',reason='自动验收：外部参照变更故障恢复后重新核验');assert wait()['phase']=='READY';calibration('texture')
    audit=request('/api/audit');(a.out/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
    with urllib.request.urlopen(a.url+'/api/audit.csv',timeout=10) as response:csv=response.read()
    assert csv.startswith(b'\xef\xbb\xbf') and b'cycle_id' in csv;(a.out/'audit.csv').write_bytes(csv)
    assert any(r['phase']=='FAULT' and r['invalidated_previous_review']=='good' for r in audit['records'])
    assert sum(r['disposition']=='release' for r in audit['records'])==2
    s=request('/api/state');summary=dict(scope='PHYSICAL_TWO_REFERENCE_CLOSED_LOOP_REPLAY_NOT_INDEPENDENT_ACCURACY',physical_inferences=len(cycles),controls_rejected=len(guards),certificates_created=len(certificates),profile_switches_without_new_bitstream=True,external_profile_change_blocked_release=True,conflict_blocked_release=True,legacy_qualification_never_bypassed_review=True,real_human_review=False,physical_camera_calibration=False,physical_actuation=False,cpu_detection=False,gpu_detection=False,final_material='texture',final_calibrated=s['closed_loop']['calibrated'],counts=s['counts'],audit_rows=len(audit['records']),csv_sha256=hashlib.sha256(csv).hexdigest())
    assert s['phase']=='READY' and s['closed_loop']['calibrated']
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
