"""Run the V167 host algorithm with a labeled score test double, never hardware."""
from pathlib import Path
import argparse,sys,json,hashlib,datetime
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'))
import frame_v167 as new,reference_tile as base,benchmark,stress_v166
import holdout
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--set',choices=['original174','opened108','fresh108'],required=True);p.add_argument('--seed-offset',type=int,default=2000000);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    declaration=dict(scope='FRESH_PROCEDURAL_EVALUATION_NOT_BOARD_NOT_REAL_PHYSICAL_ACCURACY' if a.set=='fresh108' else 'DEVELOPMENT_REPLAY_NOT_BLIND_NOT_BOARD_NOT_REAL_PHYSICAL_ACCURACY',set=a.set,implementation=new.implementation(),policy=new.policy(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),case_count=174 if a.set=='original174' else 108,seed_offset=a.seed_offset if a.set=='fresh108' else 0,generator_sha256=base.sha(Path(holdout.__file__)));(a.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n');rows=[]
    cases=([dict(c,group=c['cohort']) for c in benchmark.make_cases() if c['style']!='mvtec']+list(stress_v166.cases())) if a.set=='original174' else list(holdout.cases(declaration['seed_offset']))
    for c in cases:
        r,pair,aligned,_=new.prepare(c['reference'],c['current']);mask=None
        if pair is not None:
            words=new.oracle(pair,r['photometric']);r,mask=new.finish(r,words,dict(output_crc_verified=True,paired_sha256=r['paired_sha256'],pl_id=0x16700601,firmware=0x16700,test_double=True));r['board_integrated']=False
        truth=c['truth'];kind=c.get('kind',c.get('expected','localized_candidate' if truth.any() else 'no_candidate'));expected_alarm=True if kind in ('line','localized_candidate') else False if kind in ('good','no_candidate') else None
        passed=r['alarm'] is expected_alarm;coverage=int((mask&truth).sum())/int(truth.sum()) if truth.any() and mask is not None else 0. if truth.any() else None
        tp=int((mask&truth).sum()) if mask is not None else 0;pred=int(mask.sum()) if mask is not None else 0
        row=dict(id=c['id'],kind=kind,group=c.get('group'),passed=bool(passed),coverage=coverage,pixel_precision=tp/pred if pred else None,gt_pixels=int(truth.sum()),predicted_pixels=pred,tp=tp,parameters=c['parameters'],**r);rows.append(row)
        if not passed or (coverage is not None and coverage<.8):
            folder=a.out/c['id'];base.save_result(folder,row,mask,aligned);Image.fromarray(c['reference']).save(folder/'reference.png');Image.fromarray(c['current']).save(folder/'current.png');Image.fromarray(truth.astype(np.uint8)*255).save(folder/'truth.png')
        (a.out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(id=c['id'],kind=kind,alarm=r['alarm'],passed=bool(passed),coverage=coverage,reason=r.get('reason'))),flush=True)
    groups={}
    for kind in sorted({r['kind'] for r in rows}):
        rr=[r for r in rows if r['kind']==kind];groups[kind]=dict(n=len(rr),alarms=sum(r['alarm'] is True for r in rr),rejected=sum(r['alarm'] is None for r in rr),passed=sum(r['passed'] for r in rr),min_coverage=min((r['coverage'] for r in rr if r['coverage'] is not None),default=None))
    (a.out/'summary.json').write_text(json.dumps(dict(**declaration,groups=groups,rows=rows,accuracy_qualified=False),indent=2)+'\n')
    if new.implementation()!=declaration['implementation']:raise RuntimeError('Algorithm source changed during this run; results must not be qualified')
if __name__=='__main__':main()
