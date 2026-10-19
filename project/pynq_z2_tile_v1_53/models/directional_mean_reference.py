"""V1.54 candidate oracle: short/long directional line-mean features.

Offline only. Live PL implements the feature; neither ARM nor PC detects.
Profile: V8 seeds >90; V8/V16 support >45; short seeds/support >40/>20;
long seeds/support >48/>24. Four bounded 3x3 stages, >=3 accepted neighbors.
"""
import numpy as np
from ridge_reference import shifted
from valley_reference import valley
from weak_reference import grow


def directional_mean_score(gray,radius):
    if radius not in (8,16):raise ValueError('Supported window radii: 8,16')
    a=np.asarray(gray,dtype=np.int32)
    if a.ndim!=2 or min(a.shape)<2*radius+1 or np.any((a<0)|(a>255)):
        raise ValueError('Invalid grayscale image')
    half=radius//2-1;offset=radius//4;shift=3 if radius==8 else 4
    best=np.zeros_like(a)
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-half,half+1))+a)>>shift
        shoulder=np.minimum(shifted(mean,-offset*dy,offset*dx),shifted(mean,offset*dy,-offset*dx))
        best=np.maximum(best,shoulder-mean)
    best[:radius]=0;best[-radius:]=0;best[:,:radius]=0;best[:,-radius:]=0
    return best.astype(np.uint8)


def mask_from_scores(narrow,wide,short,long,keep,enabled=True):
    mask=(narrow>90)&keep
    weak=((narrow>45)|(wide>45))&keep
    if enabled:
        mask|=((short>40)|(long>48))&keep
        weak|=((short>20)|(long>24))&keep
    for _ in range(4):
        mask=grow(mask,weak,3)
        mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    return mask&keep


def detect(rgb,roi=(80,80,1199,639),enabled=True):
    a=np.asarray(rgb)
    if a.dtype!=np.uint8 or a.ndim!=3 or a.shape[2]!=3:raise ValueError('Expected uint8 RGB')
    a=a.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    keep=np.ones(gray.shape,bool)
    if roi is not None:
        x0,y0,x1,y1=roi
        if not 0<=x0<=x1<gray.shape[1] or not 0<=y0<=y1<gray.shape[0]:raise ValueError('ROI outside raster')
        keep[:]=False;keep[y0:y1+1,x0:x1+1]=True
    return mask_from_scores(valley(gray,8),valley(gray,16),directional_mean_score(gray,8),directional_mean_score(gray,16),keep,enabled)
