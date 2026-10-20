"""Predeclared fresh procedural patterns, never reported as real accuracy."""
from pathlib import Path
import argparse,sys,json,hashlib,datetime
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'))
import fixtures,reference_v166 as detector,reference_tile as base
def pattern(seed,kind):
    rng=np.random.default_rng(seed);a=np.empty((500,500,3),np.uint8);a[:]=rng.integers(100,210,3);im=Image.fromarray(a);d=ImageDraw.Draw(im)
    if kind==4:
        noise=rng.integers(50,205,(500,500),dtype=np.uint8);gray=np.array(Image.fromarray(noise).filter(ImageFilter.GaussianBlur(.9)))
        a=np.stack([gray,gray*.85+15,gray*.7+30],axis=-1).astype(np.uint8);im=Image.fromarray(a)
    elif kind<4:
        for i in range(55):
            x,y=rng.integers(-40,500,2);w,h=rng.integers(12,85,2);color=tuple(int(v) for v in rng.integers(45,220,3))
            if kind==0:d.ellipse([int(x),int(y),int(x+w),int(y+h)],fill=color)
            elif kind==1:d.polygon([(int(x),int(y)),(int(x+w),int(y+h//3)),(int(x+w//4),int(y+h))],fill=color)
            elif kind==2:d.rectangle([int(x),0,int(x+w//3),499],fill=color)
            else:d.line([(int(x),int(y)),(int(x+w),int(y+h)),(int(x+2*w),int(y))],fill=color,width=int(rng.integers(2,9)))
    frame=np.full((720,1280,3),27,np.uint8);frame[110:610,390:890]=np.array(im);return frame
def cases(seed_offset=0):
    for style in range(6):
        for rev in range(2):
            seed=167500+style*100+rev+seed_offset;ref=pattern(seed,style);rng=np.random.default_rng(seed+10000)
            for index in range(9):
                params=dict(dx=float(rng.uniform(-1.2,1.2)),dy=float(rng.uniform(-1.2,1.2)),gains=tuple(float(v) for v in rng.uniform(.97,1.03,3)),offsets=tuple(float(v) for v in rng.uniform(-3,3,3)),noise=float(rng.uniform(.4,1)),jpeg=int(rng.integers(94,101)),seed=seed*100+index)
                src=ref;truth=np.zeros((500,500),bool);kind='good'
                if 5<=index<=7:
                    kind='line';_,truth=fixtures.add_defect(ref,width=1 if index==5 else 2);src=ref.copy();tile=src[110:610,390:890].astype(np.int16);tile[truth]=np.clip(tile[truth]-(35 if index==5 else 60),0,255);src[110:610,390:890]=tile.astype(np.uint8)
                if index==8:kind='invalid_pose';params['dx']=6.
                yield dict(id=f'pattern_{style}_{rev}_{index}',kind=kind,reference=ref,current=fixtures.capture(src,**params),truth=truth,parameters=params)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    declaration=dict(scope='FRESH_PROCEDURAL_PATTERN_HOLDOUT_NOT_REAL_TILE_NOT_PHYSICAL_ACCURACY',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),implementation=detector.implementation(),policy=detector.policy(),generator_sha256=base.sha(__file__),case_count=108,planned_groups=dict(good=60,line=36,invalid_pose=12),tuning_allowed_after_opening=False)
    (a.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n');rows=[]
    for case in cases():
        result,mask,aligned=detector.compare(case['reference'],case['current']);kind=case['kind'];expected=None if kind=='invalid_pose' else kind=='line';passed=(result['status']=='REJECTED_INPUT' and result['alarm'] is None) if expected is None else result['status']=='COMPARED' and result['alarm'] is expected
        tp=int((mask&case['truth']).sum()) if mask is not None else 0;coverage=tp/int(case['truth'].sum()) if case['truth'].any() else None
        row=dict(id=case['id'],kind=kind,passed=bool(passed),coverage=coverage,parameters=case['parameters'],reference_array_sha256=hashlib.sha256(case['reference'].tobytes()).hexdigest(),current_array_sha256=hashlib.sha256(case['current'].tobytes()).hexdigest(),**result);rows.append(row)
        if not passed or (coverage is not None and coverage<.8):
            folder=a.out/case['id'];base.save_result(folder,row,mask,aligned)
            Image.fromarray(case['reference']).save(folder/'reference.png');Image.fromarray(case['current']).save(folder/'current.png');Image.fromarray(case['truth'].astype(np.uint8)*255).save(folder/'truth.png')
        (a.out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(id=row['id'],kind=kind,alarm=result['alarm'],passed=bool(passed),coverage=coverage)),flush=True)
    groups={}
    for kind in ('good','line','invalid_pose'):
        rr=[r for r in rows if r['kind']==kind];groups[kind]=dict(n=len(rr),alarm=sum(r['alarm'] is True for r in rr),rejected=sum(r['alarm'] is None for r in rr),passed=sum(r['passed'] for r in rr),min_coverage=min((r['coverage'] for r in rr if r['coverage'] is not None),default=None))
    (a.out/'summary.json').write_text(json.dumps(dict(**declaration,groups=groups,rows=rows,accuracy_qualified=False),indent=2)+'\n')
if __name__=='__main__':main()
