"""Offline wider-line WEAK support oracle; strong seeds are exactly V1.54."""
import numpy as np
from ridge_reference import shifted
from valley_reference import valley
from directional_mean_reference import directional_mean_score
from weak_reference import grow

def wide_line_score(gray):
    a=np.asarray(gray,dtype=np.int32)
    if a.ndim!=2 or min(a.shape)<33 or np.any((a<0)|(a>255)):raise ValueError('Expected gray >=33x33, range 0..255')
    best=np.zeros_like(a)
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-3,4))+a)>>3
        shoulders=np.minimum(shifted(mean,-4*dy,4*dx),shifted(mean,4*dy,-4*dx))
        best=np.maximum(best,shoulders-mean)
    # The added taps share the R16 window; its valid-border contract is retained.
    best[:16]=0;best[-16:]=0;best[:,:16]=0;best[:,-16:]=0
    return best.astype(np.uint8)

def mask_from_scores(narrow,wide,short,long,line,keep,low,enabled=True,passes=4):
    if type(low) is not int or not 1<=low<=255:raise ValueError('Invalid weak line threshold')
    if type(passes) is not int or passes not in (4,8):raise ValueError('Supported candidate pass counts: 4 or 8')
    seed=((narrow>90)|(short>40)|(long>48))&keep
    weak=((narrow>45)|(wide>45)|(short>20)|(long>24))&keep
    if enabled:weak|=(line>low)&keep
    mask=seed
    for _ in range(passes if enabled else 4):
        mask=grow(mask,weak,3);mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    return mask&keep

def detect(rgb,low,enabled=True,roi=(80,80,1199,639),passes=4):
    a=np.asarray(rgb)
    if a.dtype!=np.uint8 or a.ndim!=3 or a.shape[2]!=3:raise ValueError('Expected uint8 RGB')
    a=a.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    keep=np.ones(gray.shape,bool)
    if roi is not None:
        x0,y0,x1,y1=roi
        if not 0<=x0<=x1<gray.shape[1] or not 0<=y0<=y1<gray.shape[0]:raise ValueError('ROI outside raster')
        keep[:]=False;keep[y0:y1+1,x0:x1+1]=True
    return mask_from_scores(valley(gray,8),valley(gray,16),directional_mean_score(gray,8),directional_mean_score(gray,16),wide_line_score(gray),keep,low,enabled,passes)
