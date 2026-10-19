"""V1.55 offline experiments. No live-host import and no accepted profile yet."""
import numpy as np
from ridge_reference import shifted
from weak_reference import grow

DIRECTIONS=((1,0),(0,1),(1,1),(1,-1))

def direction_planes(gray,radius,normal_offset=None):
    a=np.asarray(gray,dtype=np.int32);half=radius//2-1;offset=radius//4 if normal_offset is None else normal_offset;bits=3 if radius==8 else 4
    if half+offset>radius:raise ValueError('Feature exceeds its shared gray window')
    result=[]
    for dx,dy in DIRECTIONS:
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-half,half+1))+a)>>bits
        shoulder=np.minimum(shifted(mean,-offset*dy,offset*dx),shifted(mean,offset*dy,-offset*dx))
        d=np.maximum(shoulder-mean,0)
        d[:radius]=0;d[-radius:]=0;d[:,:radius]=0;d[:,-radius:]=0
        result.append(d.astype(np.uint8))
    return np.stack(result)

def shoulder_noise(gray):
    """Mean adjacent-tangent absolute differences at both short-line shoulders."""
    a=np.asarray(gray,dtype=np.int16);result=[]
    for dx,dy in DIRECTIONS:
        edge=np.abs(shifted(a,dx,dy)-a).astype(np.int32)
        # Eight adjacent differences along each shoulder; divide by sixteen.
        line=sum(shifted(edge,dx*k,dy*k) for k in range(-4,4))
        noise=(shifted(line,-2*dy,2*dx)+shifted(line,2*dy,-2*dx))>>4
        noise[:8]=0;noise[-8:]=0;noise[:,:8]=0;noise[:,-8:]=0
        result.append(noise.astype(np.uint8))
    return np.stack(result)

def masks(narrow,wide,short,long,noise=None,adaptive=None):
    if adaptive is None:
        strong=(short>40)|(long>48);directional=(short>20)|(long>24)
    else:
        floor,shift=adaptive
        threshold=np.asarray(noise,dtype=np.int32)//(1<<shift)+floor
        strong=(short>threshold)|(long>(threshold+8))
        directional=(short>((threshold+1)//2))|(long>((threshold+9)//2))
    seed=(narrow>90)|np.any(strong,axis=0)
    weak=(narrow>45)|(wide>45)|np.any(directional,axis=0)
    return seed,weak,directional

def propagate(seed,weak,directional,passes=4,mode='support3'):
    mask=seed.copy()
    for _ in range(passes):
        if mode.startswith('support'):
            mask=grow(mask,weak,int(mode[-1]))
        else:
            following=mask.copy() if mode=='direction_only' else grow(mask,weak,3)
            for eligible,(dx,dy) in zip(directional,DIRECTIONS):
                plus=shifted(mask,dx,dy);minus=shifted(mask,-dx,-dy)
                if mode in ('tangent','direction_only'):accept=plus|minus
                elif mode=='tangent_continuity':
                    accept=(plus & shifted(eligible,-dx,-dy))|(minus & shifted(eligible,dx,dy))
                elif mode=='tangent_two':
                    accept=(plus&shifted(mask,2*dx,2*dy))|(minus&shifted(mask,-2*dx,-2*dy))|(plus&minus)
                else:raise ValueError(mode)
                following|=eligible&accept
            mask=following
        mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    return mask
