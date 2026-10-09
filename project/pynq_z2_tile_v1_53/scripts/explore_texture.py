"""Development study; historical MVTec test was already viewed in V1.4."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from regions_reference import regions
D=R/'data/real_tiles';samples=json.loads((D/'manifest.json').read_text())['samples']
def blur(a):
    y=np.pad(a.astype(np.int32),1,mode='edge');t=y[:-2,:]+2*y[1:-1,:]+y[2:,:]
    return ((t[:,:-2]+2*t[:,1:-1]+t[:,2:])>>4).astype(np.int16)
rows=[];scores={}
for i,s in enumerate(samples):
    rgb=np.asarray(Image.open(D/s['image']).convert('RGB').resize((500,500),Image.Resampling.BILINEAR),dtype=np.int32)
    gray=((77*rgb[:,:,0]+150*rgb[:,:,1]+29*rgb[:,:,2])>>8).astype(np.int16)
    fields=[]
    for n in range(3):
        if n:gray=blur(gray)
        sc=valley(gray);sc[:10]=0;sc[-10:]=0;sc[:,:10]=0;sc[:,-10:]=0
        fields.append(sc.astype(np.uint8))
    scores[s['id']]=fields
    if i%50==0:print('scores',i,flush=True)
result=[]
for n in range(3):
    # Train ONLY on known-good official training split. Conservatively limit
    # count before components; 32nd highest score is the lowest alarm threshold.
    critical=[int(np.partition(scores[s['id']][n].ravel(),-32)[-32]) for s in samples if s['split']=='train']
    for percentile in (95,99,100):
        threshold=int(np.percentile(critical,percentile,method='higher'))
        rr=[]
        for s in samples:
            if s['split']!='test':continue
            sc=scores[s['id']][n];mask=np.zeros((720,1280),bool);mask[110:610,390:890]=sc>threshold
            boxes=regions(mask)['boxes'];rr.append(dict(id=s['id'],label=s['label'],alarm=bool(boxes),candidate_pixels=int(mask.sum()),boxes=boxes))
        metrics={label:dict(n=sum(x['label']==label for x in rr),alarms=sum(x['label']==label and x['alarm'] for x in rr)) for label in sorted(set(x['label'] for x in rr))}
        result.append(dict(blur_passes=n,train_normal_percentile=percentile,threshold=threshold,metrics=metrics,items=rr))
        print(json.dumps({k:v for k,v in result[-1].items() if k!='items'}),flush=True)
(R/'reports/v15/texture_exploration.json').write_text(json.dumps(result,indent=2))
