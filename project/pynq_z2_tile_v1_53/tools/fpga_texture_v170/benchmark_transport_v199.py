"""Matched original-photo transport benchmark with exact archived PL outputs."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,hashlib,statistics
import numpy as np
from board_client import Board
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);archive=a.bundle/'verified_hdmi/evidence/all117_direct_raw.zip';model=json.loads((a.bundle/'verified_hdmi/model/graph.json').read_text())
    z=ZipFile(archive);allrows={n.split('/')[0]:json.loads(z.read(n)) for n in z.namelist() if n.endswith('/evidence.json')}
    if not a.plan.exists():
        selected=[]
        for label in ['good','crack','glue_strip','gray_stroke','oil','rough']:
            group=sorted(ident for ident,r in allrows.items() if Path(r['input']).parent.name==label)
            count=6 if label=='good' else 2;assert len(group)>=count;selected.extend(group[:count])
        assert len(selected)==16
        a.plan.write_text(json.dumps(dict(scope='MATCHED32_PHYSICAL_TRANSPORT_COMPARISON',ids=selected,rounds=2,warmup=1,model_sha256=model['sha256'],minimum_median_reduction=0.05,maximum_p95_regression=0.10,exact_results_required=True,no_hardware_or_detection_change=True),indent=2))
    plan=json.loads(a.plan.read_text());assert plan['model_sha256']==model['sha256']
    board=Board(timeout=30);h=board.request(1)[0];assert h[6]==model['crc32'];boot=h[8]
    first=allrows[plan['ids'][0]];board.infer(Path(first['input']),a.out/'warmup',model)
    results=[]
    for repeat in range(plan['rounds']):
        for ident in plan['ids']:
            old=allrows[ident];path=Path(old['input']);assert hashlib.sha256(path.read_bytes()).hexdigest()==old['input_file_sha256']
            folder=a.out/f'{repeat}_{ident}';r=board.infer(path,folder,model)
            expected=np.frombuffer(z.read(ident+'/raw_result.bin'),dtype='<u4').copy();actual=np.fromfile(folder/'raw_result.bin',dtype='<u4');expected[9]=actual[9]
            assert r['boot_identity']==boot and np.array_equal(expected,actual)
            results.append(dict(id=ident,repeat=repeat,result=r,exact_except_frame_sequence=True));(a.out/'results.json').write_text(json.dumps(results,indent=2))
            print('MATCHED_PHYSICAL_EXACT',len(results),'OF32',flush=True)
    values=[r['result']['wall_seconds'] for r in results]
    summary=dict(scope='MATCHED_ORIGINAL840_PHOTO_TRANSPORT_NOT_VIDEO_FPS',cases=len(results),model_sha256=model['sha256'],boot_identity=boot,all_scores_masks_exact_except_sequence=True,mean_seconds=statistics.mean(values),median_seconds=statistics.median(values),p95_seconds=float(np.percentile(values,95)),mean_engine_seconds=statistics.mean(r['result']['pl_engine_seconds'] for r in results),connection_retries=board.connection_retries)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
