"""V1.54 research candidate: four directional, integer line-mean dark ridges.

Offline oracle only. This module is never imported by the live workstation.
The 7-sample line duplicates its center, so division is an exact >>3.
Radius 2 normal offsets and +/-3 tangent offsets fit inside the existing R8
window. All scores have the R8 border contract, including diagonals.
"""
import numpy as np
from valley_reference import valley
from weak_reference import grow


def shifted(a, dx, dy):
    h,w=a.shape
    p=np.pad(a,((abs(dy),abs(dy)),(abs(dx),abs(dx))))
    return p[abs(dy)+dy:abs(dy)+dy+h,abs(dx)+dx:abs(dx)+dx+w]


def ridge_score(gray):
    a=np.asarray(gray,dtype=np.int32)
    if a.ndim!=2 or min(a.shape)<17 or np.any((a<0)|(a>255)):
        raise ValueError('Expected a grayscale plane at least 17x17, values 0..255')
    best=np.zeros_like(a)
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-3,4))+a)>>3
        shoulder=np.minimum(shifted(mean,-2*dy,2*dx),shifted(mean,2*dy,-2*dx))
        best=np.maximum(best,shoulder-mean)
    best[:8]=0;best[-8:]=0;best[:,:8]=0;best[:,-8:]=0
    return best.astype(np.uint8)


def mask_from_scores(narrow,wide,ridge,keep,high=90,ridge_high=24,
                     add_seeds=True,add_weak=True,passes=4):
    if not 0<=ridge_high<=255 or not 0<=high<=255 or passes not in (2,4):
        raise ValueError('Invalid detector configuration')
    mask=(narrow>high)&keep
    weak=((narrow>(high+1)//2)|(wide>(high+1)//2))&keep
    if add_seeds:mask|=(ridge>ridge_high)&keep
    if add_weak:weak|=(ridge>(ridge_high+1)//2)&keep
    for _ in range(passes):
        mask=grow(mask,weak,3)
        mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    return mask&keep


def detect(rgb,high=90,ridge_high=24,roi=(80,80,1199,639),**options):
    a=np.asarray(rgb)
    if a.ndim!=3 or a.shape[2]!=3 or a.dtype!=np.uint8:
        raise ValueError('Expected uint8 RGB input')
    a=a.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    keep=np.ones(gray.shape,bool)
    if roi is not None:
        x0,y0,x1,y1=roi
        if not 0<=x0<=x1<gray.shape[1] or not 0<=y0<=y1<gray.shape[0]:
            raise ValueError('ROI outside image')
        keep[:]=False;keep[y0:y1+1,x0:x1+1]=True
    return mask_from_scores(valley(gray,8),valley(gray,16),ridge_score(gray),keep,
                            high=high,ridge_high=ridge_high,**options)
