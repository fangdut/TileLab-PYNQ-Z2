"""Final offline oracles for two explicit V1.55 operating points; no host inference."""
import numpy as np
from ridge_reference import shifted
from valley_reference import valley
from weak_reference import grow
DIRECTIONS=((1,0),(0,1),(1,1),(1,-1))
PROFILES={'v154':dict(passes=4,kind='legacy'),
          'conservative':dict(passes=4,kind='wide_line',high=60,low=30),
          'sensitive':dict(passes=8,kind='directional')}

def line_planes(gray,half,offset,border):
    a=np.asarray(gray,dtype=np.int32);bits=3 if half==3 else 4;result=[]
    for dx,dy in DIRECTIONS:
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-half,half+1))+a)>>bits
        shoulders=np.minimum(shifted(mean,-offset*dy,offset*dx),shifted(mean,offset*dy,-offset*dx))
        score=np.maximum(shoulders-mean,0)
        score[:border]=0;score[-border:]=0;score[:,:border]=0;score[:,-border:]=0
        result.append(score.astype(np.uint8))
    return np.stack(result)

def compute_features(gray):
    a=np.asarray(gray,dtype=np.int32)
    if a.ndim!=2 or min(a.shape)<33 or np.any((a<0)|(a>255)):raise ValueError('Expected gray >=33x33, range 0..255')
    short=line_planes(a,3,2,8);long=line_planes(a,7,4,16);line=line_planes(a,3,4,16).max(axis=0)
    directions=(short>20)|(long>24)
    directions[:,:16]=False;directions[:,-16:]=False;directions[:,:,:16]=False;directions[:,:,-16:]=False
    return valley(a,8),valley(a,16),short.max(axis=0),long.max(axis=0),line,directions

def mask_from_features(features,keep,profile='v154'):
    if profile not in PROFILES:raise ValueError('Unknown fixed operating point')
    n,w,s,l,line,directions=features;spec=PROFILES[profile]
    seed=((n>90)|(s>40)|(l>48))&keep
    weak=((n>45)|(w>45)|(s>20)|(l>24))&keep
    if spec['kind']=='wide_line':seed|=(line>spec['high'])&keep;weak|=(line>spec['low'])&keep
    d=directions&keep;mask=seed
    for _ in range(spec['passes']):
        result=grow(mask,weak,3)
        if spec['kind']=='directional':
            for eligible,(dx,dy) in zip(d,DIRECTIONS):result|=eligible&(shifted(mask,dx,dy)|shifted(mask,-dx,-dy))
        mask=result;mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    return mask&keep

def detect(rgb,profile='v154',roi=(80,80,1199,639)):
    a=np.asarray(rgb)
    if a.dtype!=np.uint8 or a.ndim!=3 or a.shape[2]!=3:raise ValueError('Expected uint8 RGB')
    a=a.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8;keep=np.ones(gray.shape,bool)
    if roi is not None:
        x0,y0,x1,y1=roi
        if not 0<=x0<=x1<gray.shape[1] or not 0<=y0<=y1<gray.shape[0]:raise ValueError('ROI outside raster')
        keep[:]=False;keep[y0:y1+1,x0:x1+1]=True
    return mask_from_features(compute_features(gray),keep,profile)
