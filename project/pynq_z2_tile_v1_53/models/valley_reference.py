"""Development reference only. The live service does not call this detector."""
import numpy as np

def valley(gray, radius=8):
    y=np.asarray(gray,dtype=np.int16);h,w=y.shape;r=radius
    score=np.zeros_like(y);c=y[r:h-r,r:w-r]
    for dx,dy in ((r,0),(0,r),(r,r),(r,-r)):
        a=y[r+dy:h-r+dy,r+dx:w-r+dx]
        b=y[r-dy:h-r-dy,r-dx:w-r-dx]
        score[r:h-r,r:w-r]=np.maximum(score[r:h-r,r:w-r],np.minimum(a,b)-c)
    return score

def detect(rgb,threshold=36,radius=8,roi=(80,80,1199,639)):
    a=np.asarray(rgb,dtype=np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    score=valley(gray,radius);mask=score>threshold
    if roi:
        x0,y0,x1,y1=roi;keep=np.zeros_like(mask);keep[y0:y1+1,x0:x1+1]=True;mask&=keep
    yy,xx=np.where(mask);n=len(xx);box=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if n else None
    # A frame-level candidate gate, not a trained semantic classifier.
    alarm=bool(n>=32 and box and max(box[2]-box[0],box[3]-box[1])>=23)
    return mask,dict(candidate_pixels=n,boxes=[box] if alarm else [],alarm=alarm,
        threshold=threshold,radius=radius,algorithm='pl_opposed_valley17',provenance='OFFLINE_REFERENCE')

if __name__=='__main__':
    from pathlib import Path
    from PIL import Image
    import json
    root=Path(__file__).resolve().parents[1]
    rows=json.loads((root/'data/manifest.json').read_text())['items'];results=[]
    for row in rows:
        _,v=detect(Image.open(root/'data'/row['image']))
        results.append(dict(id=row['id'],split=row['split'],truth=row['crack'],nuisance=row['nuisance'],**v))
    summary={}
    for split in ('calibration','heldout_synthetic'):
        a=[v for v in results if v['split']==split]
        summary[split]={k:sum(bool(v['truth'])==truth and bool(v['alarm'])==pred for v in a) for k,truth,pred in [('tp',True,True),('fn',True,False),('fp',False,True),('tn',False,False)]}
    (root/'reports/valley_reference_metrics.json').write_text(json.dumps(dict(summary=summary,items=results),indent=2))
    print(json.dumps(summary))

