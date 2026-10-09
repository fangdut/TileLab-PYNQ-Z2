"""Offline acceptance oracle, never imported by the live detector/ARM runtime."""
import numpy as np
from collections import deque
def regions(mask,shift=5,limit=8):
    h,w=mask.shape;s=1<<shift;gh=(h+s-1)//s;gw=(w+s-1)//s
    cells={}
    for y in range(gh):
        for x in range(gw):
            yy,xx=np.where(mask[y*s:min(h,(y+1)*s),x*s:min(w,(x+1)*s)])
            if len(xx):cells[y*gw+x]=(len(xx),int(xx.min()+x*s),int(yy.min()+y*s),int(xx.max()+x*s),int(yy.max()+y*s))
    visited=set();boxes=[];areas=[]
    for k in sorted(cells):
        if k in visited:continue
        q=deque([k]);visited.add(k);n=0;x0=w;y0=h;x1=y1=0
        while q:
            j=q.popleft();a,l,t,r,b=cells[j];n+=a;x0=min(x0,l);y0=min(y0,t);x1=max(x1,r);y1=max(y1,b)
            cy,cx=divmod(j,gw)
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nx=cx+dx;ny=cy+dy;nk=ny*gw+nx
                    if 0<=nx<gw and 0<=ny<gh and nk in cells and nk not in visited:visited.add(nk);q.append(nk)
        if n>=32 and (x1-x0>=23 or y1-y0>=23):boxes.append([x0,y0,x1,y1]);areas.append(n)
    return dict(boxes=boxes[:limit],areas=areas[:limit],overflow=len(boxes)>limit)
