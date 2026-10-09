"""Post-holdout DEVELOPMENT experiment; never call these samples blind again."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'models')]
from valley_reference import valley
from weak_reference import grow
from regions_reference import regions

def main():
    rows=[]
    for index in (0,5,11,23):
        p=R/f'reports/v153/external_mcs2/holdout_{index:03d}_original.png'
        with Image.open(p) as im:a=np.asarray(im.convert('RGB'),np.int32)
        gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
        narrow,wide=valley(gray,8),valley(gray,16)
        keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True
        with Image.open(R/f'data/independent_mcs2/truth/holdout_{index:03d}.png') as im:truth=np.asarray(im.convert('L'))>0
        for high in (8,12,16,20,24,32,45,60,90):
            mask=(narrow>high)&keep;weak=((narrow>(high+1)//2)|(wide>(high+1)//2))&keep
            for _ in range(4):mask=grow(mask,weak,3)
            b=regions(mask);tp=int((mask&truth).sum());fp=int((mask&~truth).sum());fn=int((~mask&truth).sum())
            rows.append(dict(index=index,high=high,alarm=bool(b['boxes']),pixels=int(mask.sum()),tp=tp,fp=fp,fn=fn,recall=tp/(tp+fn),precision=tp/(tp+fp) if tp+fp else 0.))
    out=R/'reports/v153/smooth_development_experiment.json'
    out.write_text(json.dumps(dict(scope='Four previously inspected external samples; post-holdout development only. No normal-image acceptance inferred.',items=rows),indent=2))
    for high in (8,12,16,20,24,32,45,60,90):
        a=[r for r in rows if r['high']==high];tp=sum(x['tp'] for x in a);fp=sum(x['fp'] for x in a);fn=sum(x['fn'] for x in a)
        print(json.dumps(dict(high=high,alarms=sum(x['alarm'] for x in a),recall=tp/(tp+fn),precision=tp/(tp+fp) if tp+fp else 0.)))

if __name__=='__main__':main()
