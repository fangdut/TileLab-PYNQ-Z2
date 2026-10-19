"""Offline reference for PL regional evidence. No live-host or ARM image inference."""
from collections import deque
import numpy as np
MIN_TRUSTED=16
EVIDENCE_SHIFT=2

def quality_regions(mask,trusted,enabled=True,shift=5,limit=8):
    if mask.shape!=trusted.shape or mask.ndim!=2:raise ValueError('Aligned two-dimensional masks required')
    h,w=mask.shape;s=1<<shift;gh=(h+s-1)//s;gw=(w+s-1)//s
    cells={}
    for y in range(gh):
        for x in range(gw):
            block=mask[y*s:min(h,(y+1)*s),x*s:min(w,(x+1)*s)];yy,xx=np.where(block)
            if len(xx):cells[y*gw+x]=(len(xx),int(trusted[y*s:min(h,(y+1)*s),x*s:min(w,(x+1)*s)][yy,xx].sum()),int(xx.min()+x*s),int(yy.min()+y*s),int(xx.max()+x*s),int(yy.max()+y*s))
    visited=set();boxes=[];areas=[];evidence=[]
    for k in sorted(cells):
        if k in visited:continue
        q=deque([k]);visited.add(k);n=t=0;x0=w;y0=h;x1=y1=0
        while q:
            j=q.popleft();a,b,l,u,r,v=cells[j];n+=a;t+=b;x0=min(x0,l);y0=min(y0,u);x1=max(x1,r);y1=max(y1,v)
            cy,cx=divmod(j,gw)
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nx=cx+dx;ny=cy+dy;nk=ny*gw+nx
                    if 0<=nx<gw and 0<=ny<gh and nk in cells and nk not in visited:visited.add(nk);q.append(nk)
        if n>=32 and (x1-x0>=23 or y1-y0>=23) and (not enabled or (t>=MIN_TRUSTED and (t<<EVIDENCE_SHIFT)>=n)):
            boxes.append([x0,y0,x1,y1]);areas.append(n);evidence.append(t)
    return dict(boxes=boxes[:limit],areas=areas[:limit],trusted=evidence[:limit],overflow=len(boxes)>limit)
