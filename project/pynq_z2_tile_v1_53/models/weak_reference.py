"""Two or four local hysteresis stages, bounded memory/latency; no live host detection."""
import numpy as np
from valley_reference import valley
def grow(mask,weak,min_neighbors=1):
 p=np.pad(mask,1);n=np.zeros(mask.shape,np.uint8)
 for y in range(3):
  for x in range(3):n+=p[y:y+mask.shape[0],x:x+mask.shape[1]]
 return mask | (weak & (n>=min_neighbors))
def detect(rgb,threshold=89,low_ratio=2,min_neighbors=3,roi=(80,80,1199,639),passes=2):
 if passes not in (2,4):raise ValueError('Supported bounded growth: 2 or 4 passes')
 a=np.asarray(rgb,dtype=np.int32);s=valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8)
 keep=np.zeros(s.shape,bool);x0,y0,x1,y1=roi;keep[y0:y1+1,x0:x1+1]=1
 high=(s>threshold)&keep;low=threshold-(threshold>>2) if low_ratio==3 else (threshold+1)//2
 weak=(s>low)&keep;mask=high
 for _ in range(passes):mask=grow(mask,weak,min_neighbors)
 return mask,dict(high=threshold,low=low,min_neighbors=min_neighbors,passes=passes)
