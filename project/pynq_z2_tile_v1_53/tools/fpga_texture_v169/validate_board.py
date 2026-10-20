"""Run fixed real-photo board cases, then compare with offline score maps.
The comparison is verification only. Board masks/alarms are never corrected.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from board_client import Board
def reference_mask(grid,width,height,threshold):
    # Independent offline result checker; never used to replace a PL result.
    x=np.clip((np.arange(width,dtype=np.float32)+.5)*np.float32(56/width)-.5,0,55)
    y=np.clip((np.arange(height,dtype=np.float32)+.5)*np.float32(56/height)-.5,0,55)
    x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,55);y1=np.minimum(y0+1,55)
    fx=x-x0;fy=(y-y0)[:,None]
    top=grid[y0[:,None],x0]*(1-fx)+grid[y0[:,None],x1]*fx
    bottom=grid[y1[:,None],x0]*(1-fx)+grid[y1[:,None],x1]*fx
    return top*(1-fy)+bottom*fy>threshold
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--board',default='192.168.33.10');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    images=json.loads((a.dataset/'manifest.json').read_text())['images'];rows=json.loads((a.model/'results.json').read_text());reference={v['id']:v for v in rows}
    cases=[next(v for v in images if v['role']=='test' and v['label']==label) for label in ('good','crack')]
    plan=dict(scope='INITIAL_BOARD_MIGRATION_CHECK_NOT_FULL_ACCURACY_BENCHMARK',ids=[v['id'] for v in cases],labels=[v['label'] for v in cases],selection='First manifest test good and first manifest test crack; selected before board results',max_grid_error=1e-3)
    (a.out/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan),flush=True)
    b=Board(a.board);model=b.upload(a.model);proof=[]
    for index,item in enumerate(cases):
        print(f'Starting PL case {index+1}/{len(cases)}: {item["id"]} {item["label"]}',flush=True)
        folder=a.out/item['id'];evidence=b.infer(a.dataset/item['file'],folder,model)
        actual=np.load(folder/'scores.npy');expected=np.load(a.model/(item['id']+'_scores.npy'))
        error=float(np.max(np.abs(actual-expected)));same=bool(evidence['pl_image_alarm']==reference[item['id']]['alarm'])
        words=np.fromfile(folder/'raw_result.bin',dtype='<u4');mask=words[16+56*56:].reshape(evidence['height'],evidence['width']).astype(bool)
        frozen_mask=reference_mask(expected,evidence['width'],evidence['height'],evidence['pl_threshold'])
        union=int(np.count_nonzero(mask|frozen_mask));intersection=int(np.count_nonzero(mask&frozen_mask))
        iou=intersection/union if union else 1.;agreement=float(np.mean(mask==frozen_mask))
        check=dict(id=item['id'],label=item['label'],max_grid_error=error,alarm_matches_frozen_reference=same,mask_iou_with_frozen_reference=iou,mask_pixel_agreement=agreement,ground_truth_correct=bool(evidence['pl_image_alarm']==(item['label']!='good')),wall_seconds=evidence['wall_seconds'],result_sha256=evidence['result_sha256'])
        (folder/'reference_check.json').write_text(json.dumps(check,indent=2));proof.append(check)
        (a.out/'progress.json').write_text(json.dumps(proof,indent=2))
        if not same or error>1e-3 or agreement<.999 or iou<.99:raise RuntimeError('Board/reference disagreement; do not accept or modify results')
    summary=dict(scope=plan['scope'],cases=len(proof),all_alarms_match=True,all_grid_errors_below_0_001=True,max_grid_error=max(v['max_grid_error'] for v in proof),mean_wall_seconds=float(np.mean([v['wall_seconds'] for v in proof])),cases_details=proof,
        offline_historical_benchmark=json.loads((a.model/'summary.json').read_text()),claim='Two initial real-photo board cases passed. This is not a 117-image board accuracy measurement or a general-material validation.')
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
