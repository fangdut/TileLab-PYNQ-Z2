"""Replay rejected clip4 development ablation; do not call it a holdout."""
from pathlib import Path
import argparse,json,sys,numpy as np
from PIL import Image
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();W=a.workspace;a.out.mkdir(exist_ok=False)
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'experimental/texture_profiles_v197'))
    from reference import sample_rgb,extract
    model=json.loads((W/'v197_new80_01/frozen_model.json').read_text())['model'];rep=np.array(model['representatives'])
    def f(row):
        y=sample_rgb(Image.open(Path(row['base'])/row['file']).convert('RGB'));stats=extract(y);g=int(np.abs(rep-stats['descriptor']).sum(1).argmin());scores=[]
        for d in [2,4,8]:
            r=np.clip(2*y[:,d:256-d]-y[:,:256-2*d]-y[:,2*d:],-4,4);n=r.sum(0);e=np.abs(r).sum(0);scores.append(int((n*n//(e+1)).max()))
        return dict(id=row['id'],label=row['label'],group=g,scores=scores)
    normal=json.loads((W/'v197_expanded01/normal_manifest.json').read_text());cal=[f(r) for r in normal if r['role']=='calibration'];thresholds={str(g):[max(r['scores'][i] for r in cal if r['group']==g)+1 for i in range(3)] for g in range(8)}
    rows=[]
    for name in ['v196_dataset_hfe01','v196_hfe_holdout01','v197_new80_01']:
        rows += [f(dict(r,base=str(W/name))) for r in json.loads((W/name/'manifest.json').read_text())['images'] if r.get('role','test')=='test']
    for row in rows:row['alarm']=any(s>t for s,t in zip(row['scores'],thresholds[str(row['group'])]))
    tp=sum(r['label']=='defect' and r['alarm'] for r in rows);fp=sum(r['label']=='good' and r['alarm'] for r in rows)
    (a.out/'summary.json').write_text(json.dumps(dict(scope='EXPOSED160_DEVELOPMENT_NOT_BOARD',tp=tp,fp=fp,tn=80-fp,fn=80-tp),indent=2),encoding='utf8')
    (a.out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
if __name__=='__main__':main()
