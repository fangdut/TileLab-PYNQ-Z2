"""OFFLINE bit-accurate reference for source=3,e=1 (not the runtime detector)."""
import numpy as np

def detect(rgb, threshold=12, roi=(80,80,1199,639)):
    a=np.asarray(rgb,dtype=np.int32)
    y=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    h,w=y.shape;s=np.zeros_like(y)
    for j,row in enumerate(((1,2,1),(2,4,2),(1,2,1))):
        for i,k in enumerate(row):s[1:-1,1:-1]+=k*y[j:j+h-2,i:i+w-2]
    d=np.maximum((s>>4)-y,0);mask=d>threshold
    if roi:
        x0,y0,x1,y1=roi
        if not 0<=x0<=x1<w or not 0<=y0<=y1<h:raise ValueError('ROI outside image')
        keep=np.zeros_like(mask);keep[y0:y1+1,x0:x1+1]=True;mask&=keep
    yy,xx=np.where(mask);n=len(xx)
    box=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if n else None
    alarm=bool(n>=32 and box and max(box[2]-box[0],box[3]-box[1])>=23)
    return mask,dict(candidate_pixels=n,boxes=[box] if alarm else [],alarm=alarm,
                    threshold=threshold,algorithm='pl_local_contrast_v1',
                    provenance='OFFLINE_REFERENCE',limitations='single global box; not CCL')

def metrics(mask,truth):
    t=np.asarray(truth,dtype=bool);p=np.asarray(mask,dtype=bool)
    tp=int((t&p).sum());fp=int((~t&p).sum());fn=int((t&~p).sum())
    return dict(tp=tp,fp=fp,fn=fn,pixel_recall=tp/(tp+fn) if tp+fn else None,
                pixel_precision=tp/(tp+fp) if tp+fp else None,iou=tp/(tp+fp+fn) if tp+fp+fn else None)
