"""Offline integer oracle for adaptive line calibration; no station import."""
import numpy as np
SPANS=(2,4,8)
def sample_rgb(rgb):
    rgb=np.asarray(rgb,dtype=np.int64);h,w=rgb.shape[:2]
    if (w,h)!=(256,704):raise ValueError('Frozen pilot requires 256x704')
    yy=np.clip((2*np.arange(224)+1)*h-224,0,(h-1)*448)//448
    return ((rgb[:,:,0]+2*rgb[:,:,1]+rgb[:,:,2])//4)[yy]
def extract(samples):
    y=np.asarray(samples,dtype=np.int64)
    if y.shape!=(224,256) or y.min()<0 or y.max()>255:raise ValueError('Expected224x256 Y samples')
    hist=np.bincount((y//16).ravel(),minlength=16)//224
    energy=[];signed=[];absolute=[]
    for d in SPANS:
        r=2*y[:,d:256-d]-y[:,:256-2*d]-y[:,2*d:]
        n=r.sum(0);e=np.abs(r).sum(0);signed.append(n);absolute.append(e)
        energy.append(int(np.abs(r).sum()//r.size)*4)
    return dict(descriptor=np.r_[hist,energy],signed=signed,absolute=absolute)
def decide(stats,model):
    rep=np.asarray(model['representatives'],dtype=np.int64);desc=stats['descriptor']
    group=int(np.abs(rep-desc).sum(1).argmin())
    thresholds=model['thresholds'].get(str(group))
    if thresholds is None:raise ValueError('Uncalibrated reference group')
    flags=np.zeros((256,3),dtype=np.uint8);scores=np.zeros((256,3),dtype=np.int64)
    for i,d in enumerate(SPANS):
        n=stats['signed'][i];e=stats['absolute'][i];t=thresholds['weighted'][i]
        scores[d:256-d,i]=n*n//(e+1)
        flags[d:256-d,i]=n*n>=(int(t)+1)*(e+1)
    return dict(group=group,alarm=bool(flags.any()),flags=flags,scores=scores)
