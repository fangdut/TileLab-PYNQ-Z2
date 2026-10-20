"""Actual V164 PL replay after headless transport fix, not V166 accuracy.

The independent CPU oracle is used after saving hardware evidence. It never
supplies masks, boxes or decisions to the board or live workstation.
"""
from pathlib import Path
import argparse,datetime,hashlib,io,itertools,json,sys,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host'));sys.path.insert(0,str(ROOT/'tools/single_tile'))
from single_tile_station import SingleTileBridge
from stimulus_command import make_command
from workstation import atomic
from detector import infer,load
from fine_integer_native import NativeBoost

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--address',default='192.168.33.10');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--native-library',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    modelpath=ROOT/'models/v159_integer_model.json';model=json.loads(modelpath.read_text());p=load(ROOT);backend=NativeBoost(model,a.native_library)
    rows=json.loads((ROOT/'data/real_tiles/hdmi_manifest.json').read_text())['items'];rows=[r for r in rows if r['index'] in list(range(17))+list(range(35,68))]
    bridge=SingleTileBridge(a.address);pre=bridge.stats();report=dict(scope='ACTUAL_V164_PL_HEADLESS_TRANSPORT_DEVELOPMENT_REPLAY_NOT_V166_REFERENCE_MODE_NOT_INDEPENDENT_ACCURACY',accuracy_qualified=False,board_acceptance_scope='Captured-pixel arithmetic and transport consistency only',model_sha256=hashlib.sha256(modelpath.read_bytes()).hexdigest(),profile_sha256=p['profile_sha256'],preflight=pre,rows=[])
    try:
        bridge.configure(90)
        def show(name):
            payload,request_id=make_command(name);atomic(ROOT/'host/display_command.txt',payload);deadline=time.monotonic()+10
            while True:
                try:player=json.loads((ROOT/'host/player_status.json').read_text())
                except (OSError,json.JSONDecodeError):player={}
                if player.get('source')==name and player.get('request_id')==request_id and not player.get('error'):break
                if time.monotonic()>deadline:raise TimeoutError('HDMI player did not adopt '+name)
                time.sleep(.1)
            time.sleep(.4)
        drain=0
        for index,item in enumerate(rows):
            # Product queue deliberately preserves earlier events. An empty field
            # closes the previous tile; archive pending evidence before ACK.
            show('station_6')
            for _ in range(24):
                if bridge.stats()['depth']==0:break
                stale,old_image,old_mask=bridge.capture(90);folder=a.out/f'prior_queue_{drain:03}';folder.mkdir();drain+=1
                atomic(folder/'hardware.json',(json.dumps(stale,indent=2)+'\n').encode());atomic(folder/'original.png',old_image);atomic(folder/'pl_mask.png',old_mask);bridge.ack(stale)
            else:raise RuntimeError('Pending queue did not settle; no source-labelled measurement made')
            name=f"real_{item['index']:03}";show(name);frame,png,pl_png=bridge.capture(90)
            folder=a.out/name;folder.mkdir();atomic(folder/'original.png',png);atomic(folder/'pl_mask.png',pl_png);atomic(folder/'hardware.json',(json.dumps(frame,indent=2)+'\n').encode())
            image=np.array(Image.open(io.BytesIO(png)).convert('RGB'));mask=np.array(Image.open(io.BytesIO(pl_png)).convert('L'))>0
            expected,result=infer(image,model,backend);different=int(np.count_nonzero(mask!=expected))
            with Image.open(ROOT/'data/real_tiles'/item['image']) as im:source=np.array(im.convert('RGB'))[110:610,390:890].astype(float)
            current=image[110:610,390:890].astype(float);best=-1.
            # HDMI byte/color chain can differ from the original source. Pose/source
            # check only; the detector oracle ALWAYS sees the actual captured RGB.
            for order in itertools.permutations(range(3)):
                channels=[]
                for ci,cj in enumerate(order):
                    x=source[...,ci].ravel();y=current[...,cj].ravel();x=x-x.mean();y=y-y.mean();den=np.sqrt((x*x).mean()*(y*y).mean())
                    if den>0:channels.append(float((x*y).mean()/den))
                if channels:best=max(best,float(np.mean(channels)))
            passed=different==0 and frame['alarm']==result['alarm'] and frame['boxes']==result['regions']['boxes'] and best>.9
            row=dict(source=name,label=item['label'],source_id=item['id'],source_path=item['image'],source_sha256=hashlib.sha256((ROOT/'data/real_tiles'/item['image']).read_bytes()).hexdigest(),captured_sha256=hashlib.sha256(png).hexdigest(),mask_sha256=hashlib.sha256(pl_png).hexdigest(),source_color_permutation_ncc=best,mask_mismatch_pixels=different,arithmetic_and_transport_passed=passed,hardware=frame,oracle=result)
            atomic(folder/'comparison.json',(json.dumps(row,indent=2)+'\n').encode());bridge.ack(frame)
            report['rows'].append(row);atomic(a.out/'progress.json',(json.dumps(report,indent=2)+'\n').encode());print(json.dumps(dict(index=index+1,source=name,alarm=frame['alarm'],mismatch=different,source_ncc=best,passed=passed)),flush=True)
            if not passed:raise AssertionError('PL/source consistency failed; saved evidence is retained')
        report.update(hardware_consistency_passed=True,postflight=bridge.stats(),captured_images=len(rows),capture_pipeline='PC HDMI -> PYNQ-Z2 PL -> DDR -> Ethernet',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        atomic(a.out/'summary.json',(json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
    finally:bridge.close()

if __name__=='__main__':main()
