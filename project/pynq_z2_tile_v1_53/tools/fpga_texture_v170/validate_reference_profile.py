"""Physical reference-profile validation; host reference is post-hoc audit.

All operational alarms, grids and masks come from the PL. This test harness
compares already frozen expected arrays only after receiving board results.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from board_client import Board
from validate_board import mask_ref

def main():
    p=argparse.ArgumentParser()
    for name in ['dataset','profile','program','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--regression-dataset',type=Path);p.add_argument('--board',default='192.168.33.10')
    a=p.parse_args();a.out.mkdir(exist_ok=False)
    def save(name,obj):(a.out/name).write_text(json.dumps(obj,indent=2),encoding='utf8')
    rows=[]
    for group,folder in [('new_test',a.dataset),('exposed_regression',a.regression_dataset)]:
        if folder:
            rows.extend(dict(r,group=group,dataset=str(folder)) for r in json.loads((folder/'manifest.json').read_text(encoding='utf8'))['images'] if r['role']=='test')
    assert len({r['original_sha256'] for r in rows})==len(rows)
    identity=json.loads((a.program/'identity.json').read_text(encoding='utf8'))
    graph=json.loads((a.profile/'graph.json').read_text(encoding='utf8'))
    save('plan.json',dict(rows=rows,model_sha256=graph['sha256'],program=identity,
        scope='ROOF_CERAMIC_REFERENCE_TRANSFER_PILOT_NOT_FLOOR_ACCEPTANCE',
        input_is_offline_720_derivative=True,threshold_changes_during_test=False))
    board=Board(a.board);model=board.upload(a.profile);results=[];last=None;start=time.monotonic()
    for i,r in enumerate(rows):
        path=Path(r['dataset'])/r['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==r['prepared_sha256']
        folder=a.out/r['id'];e=board.infer(path,folder,model)
        assert e['boot_identity']==identity['boot_identity']
        assert e['model_sha256']==identity['build']['model_sha256']
        if last is not None:assert e['pl_frame_sequence']==last+1
        last=e['pl_frame_sequence'];expected=np.load(a.profile/(r['id']+'_scores.npy'),allow_pickle=False)
        actual=np.load(folder/'scores.npy');grid_error=int(np.abs(actual.astype('i8')-expected).max())
        wire=np.fromfile(folder/'raw_result.bin',dtype='<u4');mask=wire[16+model['grid']**2:].reshape(e['height'],e['width'])
        mismatches=int(np.count_nonzero(mask!=mask_ref(expected,e['width'],e['height'],model['threshold'])))
        assert grid_error==0 and mismatches==0
        results.append(dict(id=r['id'],label=r['label'],group=r['group'],alarm=e['pl_image_alarm'],score=e['pl_peak'],
            max_grid_error=grid_error,mask_mismatches=mismatches,frame_sequence=last,
            model_sha256=e['model_sha256'],boot_identity=e['boot_identity'],engine_seconds=e['pl_engine_seconds']))
        save('progress.json',results);print(f'{i+1}/{len(rows)} exact',flush=True)
    def metrics(group):
        subset=[r for r in results if r['group']==group];normal=[r for r in subset if r['label']=='good'];defect=[r for r in subset if r['label']!='good']
        tp=sum(r['alarm'] for r in defect);fp=sum(r['alarm'] for r in normal)
        return dict(cases=len(subset),tp=tp,fp=fp,tn=len(normal)-fp,fn=len(defect)-tp,
            accuracy=(tp+len(normal)-fp)/len(subset),normal_false_positive_rate=fp/len(normal),defect_recall=tp/len(defect))
    summary=dict(cases=len(results),groups={g:metrics(g) for g in sorted({r['group'] for r in results})},
        all_scores_and_masks_exact=True,model_sha256=graph['sha256'],boot_identity=identity['boot_identity'],
        mean_engine_seconds=float(np.mean([r['engine_seconds'] for r in results])),wall_seconds=time.monotonic()-start,
        cpu_detection=False,gpu_detection=False,arm_transport_running=True,
        scope='ROOF_CERAMIC_REFERENCE_TRANSFER_PILOT_NOT_FLOOR_ACCEPTANCE',accepted_for_automatic_release=False)
    save('summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
