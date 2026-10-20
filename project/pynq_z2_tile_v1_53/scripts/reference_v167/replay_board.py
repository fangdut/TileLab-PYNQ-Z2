"""Full HDMI -> DDR -> host registration -> FPGA score -> result acceptance."""
from pathlib import Path
import argparse,sys,json,time,hashlib,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'host'));sys.path.insert(0,str(R/'tools/reference_tile'))
from workstation import atomic
from reference_capture import Capture
from reference_station import Station
from reference_frame_tcp import inspect as engine
import frame_v167
def main():
    p=argparse.ArgumentParser();p.add_argument('--player',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--address',default='192.168.33.10');p.add_argument('--program-proof',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    program=json.loads(a.program_proof.read_text());initial=Capture(a.address).status()
    if not program['programmed'] or initial['boot_id']!=program['boot_id']:raise ValueError('Board boot does not match the verified programming record')
    implementation=frame_v167.implementation()
    rows=json.loads((a.player/'manifest.json').read_text())['rows'];station=Station(a.address,a.out/'station');captures=Capture(a.address);results=[]
    def show(name):
        import uuid
        nonce=uuid.uuid4().hex;atomic(a.player/'host/display_command.txt',f'TILE_CMD_V1 {nonce} {name}\n'.encode());deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:state=json.loads((a.player/'host/player_status.json').read_text())
            except (OSError,json.JSONDecodeError):state={}
            if state.get('source')==name and state.get('request_id')==nonce and not state.get('error'):time.sleep(.45);return
            time.sleep(.1)
        raise TimeoutError('Player adoption failed: '+name)
    for row in rows:
        show(row['source']);kind=row['kind'];pattern=row['style'];started=time.perf_counter()
        result=station.action(dict(op='calibrate' if kind=='reference' else 'inspect',pattern=pattern,declared_good=True))
        record=dict(source=row,seconds=time.perf_counter()-started,result=result)
        identity=result['reference']['capture_identity'] if kind=='reference' else result['capture']
        if identity['boot_id']!=initial['boot_id']:raise ValueError('Board restarted during replay')
        if kind!='reference':
            folder=station.store/result['record'];current=np.array(Image.open(folder/'capture/input.png').convert('RGB'));active=json.loads((station.calibrations/pattern/'active.json').read_text());ref=np.array(Image.open(station.store/active['bundle']/'reference.png').convert('RGB'))
            prepared,paired,_,_=frame_v167.prepare(ref,current)
            if paired is not None:
                actual=np.fromfile(folder/'scores.u32',dtype='<u4').reshape(500,500);expected=frame_v167.oracle(paired,prepared['photometric']);mismatch=int(np.count_nonzero(actual!=expected));record['score_mismatch_pixels']=mismatch
                if mismatch:raise AssertionError('Full-frame PL mismatch: '+row['source'])
            expected_status='REJECTED_INPUT' if kind=='invalid_pose' else 'COMPARED';expected_alarm=None if kind=='invalid_pose' else kind=='line'
            passed=result['status']==expected_status and result['alarm'] is expected_alarm;record['expectation_passed']=passed
            if not passed:
                atomic(a.out/'failed_case.json',(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode());raise AssertionError('HDMI reference outcome differs: '+row['source'])
        results.append(record);atomic(a.out/'progress.json',(json.dumps(results,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(dict(source=row['source'],kind=kind,status=result['status'],alarm=result.get('alarm'),seconds=record['seconds'])),flush=True)
    if implementation!=frame_v167.implementation():raise ValueError('Algorithm source changed during replay')
    proof=dict(scope='ACTUAL_HDMI_REFERENCE_PIPELINE_PROCEDURAL_NOT_PHYSICAL_TILE_ACCURACY',passed=True,accuracy_qualified=False,preparation_partition='HOST',metric_partition='PL',components_partition='HOST',implementation_sha256=implementation,programming=program,programming_record_sha256=hashlib.sha256(a.program_proof.read_bytes()).hexdigest(),replay_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=results,board=captures.status())
    atomic(a.out/'summary.json',(json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode())
if __name__=='__main__':main()
