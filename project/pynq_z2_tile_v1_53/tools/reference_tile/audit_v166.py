"""Reproducible development replay; synthetic cases are not qualification."""
from pathlib import Path
import argparse,hashlib,json,datetime
import numpy as np
from PIL import Image
import benchmark,stress_v166,reference_v166 as candidate,reference_tile as base

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    cases=[dict(c,group=c['cohort']) for c in benchmark.make_cases() if c['style']!='mvtec']+list(stress_v166.cases())
    declaration=dict(scope='SYNTHETIC_DEVELOPMENT_MECHANISM_REPLAY_NOT_REAL_ACCURACY_NOT_BOARD_NOT_BLIND',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),implementation=candidate.implementation(),policy=candidate.policy(),source_sha256={n:base.sha(Path(__file__).with_name(n)) for n in ('fixtures.py','benchmark.py','stress_v166.py','audit_v166.py')},cases=[{k:v for k,v in c.items() if k not in ('reference','current','truth')} for c in cases])
    (a.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n',encoding='utf8');rows=[]
    for index,c in enumerate(cases):
        r,m,aligned=candidate.compare(c['reference'],c['current']);truth=c['truth'];tp=int((m&truth).sum()) if m is not None else 0;fp=int((m&~truth).sum()) if m is not None else 0
        expected=c.get('expected','localized_candidate' if truth.any() else 'no_candidate')
        met=(r['status']=='COMPARED' and not r['alarm']) if expected=='no_candidate' else (bool(r['alarm']) and tp>0) if expected=='localized_candidate' else r['alarm'] is not False
        row=dict(id=c['id'],group=c['group'],parameters=c['parameters'],expected=expected,met=bool(met),gt_pixels=int(truth.sum()),tp=tp,fp=fp,pixel_coverage=tp/int(truth.sum()) if truth.any() else None,current_array_sha256=hashlib.sha256(c['current'].tobytes()).hexdigest(),reference_array_sha256=hashlib.sha256(c['reference'].tobytes()).hexdigest(),**r);rows.append(row)
        out=a.out/c['id'];base.save_result(out,row,m,aligned)
        for key in ('reference','current'):Image.fromarray(c[key]).save(out/(key+'.png'))
        Image.fromarray(truth.astype(np.uint8)*255).save(out/'truth.png')
        print(json.dumps(dict(index=index+1,total=len(cases),id=c['id'],alarm=r['alarm'],met=bool(met),coverage=row['pixel_coverage'])),flush=True)
    groups={}
    for group in sorted({r['group'] for r in rows}):
        s=[r for r in rows if r['group']==group];groups[group]=dict(cases=len(s),alarms=sum(r['alarm'] is True for r in s),rejected=sum(r['alarm'] is None for r in s),no_candidate=sum(r['alarm'] is False for r in s),localized=sum(r['tp']>0 for r in s),minimum_pixel_coverage=min((r['pixel_coverage'] for r in s if r['pixel_coverage'] is not None),default=None))
    result=dict(scope=declaration['scope'],accuracy_qualified=False,board_integrated=False,real_positive_pairs=0,implementation=candidate.implementation(),groups=groups,failures=[r['id'] for r in rows if not r['met']],rows=rows)
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
