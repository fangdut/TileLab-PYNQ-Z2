"""Bounded historical diagnostic; no candidate selection, live writes or image copies."""
from pathlib import Path
import datetime, hashlib, io, json, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parents[1]
O=R/'reports/v151/miss_diagnostic'
B=R.parent/'pynq_z2_tile_v1_50/reports/v150/band_candidate'
sys.path.insert(0,str(R/'models'))

def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
    with (O/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def main():
    O.mkdir(parents=True,exist_ok=False)
    old=json.loads((B/'declaration.json').read_bytes())
    inputs={}
    def register(p,expected=None):
        p=Path(p).resolve();b=p.read_bytes();h=sha(b)
        if expected is not None:assert h==expected,('Input changed',str(p))
        inputs[str(p)]=h
        return b
    register(B/'declaration.json');register(B/'result.json')
    for p in [__file__]+[str(R/'models'/n) for n in ('miss_diagnostics.py','weak_reference.py','valley_reference.py','regions_reference.py')]:register(p)
    for row in old['regression']:
        for p in (row['image'],row['mask']):
            if p:register(p,old['input_files'][p]['sha256'])
    save('declaration.json',dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Offline attribution on reused development images; not an improved detector or independent accuracy test',
        baseline=dict(high=90,low=45,passes=4,support=3),
        cause_order=['outside_roi','response_at_or_below_low','no_seed_within_growth_radius',
                     'no_weak_path_within_growth_steps','three_neighbor_support_requirement'],
        reachability_steps=[1,2,4,8,16,32],inputs=inputs,regression=old['regression']))
    import numpy as np
    from PIL import Image
    from valley_reference import valley
    from miss_diagnostics import diagnose,box_coverage
    from regions_reference import regions
    roi=np.zeros((720,1280),bool);roi[80:640,80:1200]=True
    def image(p):
        b=Path(p).read_bytes();assert sha(b)==inputs[p]
        with Image.open(io.BytesIO(b)) as im:return im.copy()
    rows=[];counts=dict(crack_alarms=0,good_alarms=0,tp=0,fp=0,fn=0,truth=0,seed_truth=0,covered_truth=0)
    cats={};bands={};curves={}
    for item in old['regression']:
        with image(item['image']) as im:a=np.asarray(im.convert('RGB'),np.int32)
        assert a.shape==(720,1280,3)
        s=valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8)
        t=np.zeros_like(roi)
        if item['mask']:
            with image(item['mask']) as im:t[110:610,390:890]=np.asarray(im.convert('L').resize((500,500),Image.Resampling.NEAREST))>0
        mask,d=diagnose(s,t,roi);reg=regions(mask);cov=box_coverage(t,reg['boxes'])
        alarm=bool(reg['boxes'] or reg['overflow']);counts[item['label']+'_alarms']+=int(alarm)
        if item['label']=='crack':
            for k in ('tp','fp','fn','truth','seed_truth'):counts[k]+=d[k]
            counts['covered_truth']+=cov['covered_truth']
            for k,v in d['categories'].items():cats[k]=cats.get(k,0)+v
            for k,v in d['score_bands'].items():
                b=bands.setdefault(k,dict(truth=0,missed=0))
                for n in b:b[n]+=v[n]
            for c in d['optimistic_reachability']:
                b=curves.setdefault(c['steps'],dict(unconstrained_truth=0,weak_connected_truth=0))
                for n in b:b[n]+=c[n]
        rows.append(dict(id=item['id'],label=item['label'],diagnostic=d,regions=reg,box_coverage=cov))
        if len(rows)%10==0:print(f'Diagnostic {len(rows)}/50',flush=True)
    expected=dict(crack_alarms=17,good_alarms=0,tp=24801,fp=339,fn=69242)
    assert all(counts[k]==v for k,v in expected.items()),counts
    assert sum(cats.values())==counts['fn'] and counts['tp']+counts['fn']==counts['truth']
    for p,h in inputs.items():assert sha(Path(p).read_bytes())==h,('Changed',p)
    save('items.json',rows)
    result=dict(completed=True,baseline_reproduced=True,production_changed=False,board_tested=False,
        counts=counts,categories=cats,score_bands=bands,optimistic_reachability=curves,
        pixel_recall=counts['tp']/counts['truth'],pixel_precision=counts['tp']/(counts['tp']+counts['fp']),
        displayed_box_gt_coverage=counts['covered_truth']/counts['truth'],
        declaration_sha256=sha((O/'declaration.json').read_bytes()),
        limits=['Diagnostics use repeatedly reused development frames and masks',
                'Box coverage is not segmentation accuracy and can be inflated by broad boxes',
                'Reachability bounds ignore false positives, resource and timing costs; not proposed detectors'])
    save('result.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
