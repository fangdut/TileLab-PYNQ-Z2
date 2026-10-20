import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,'D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/tools/reference_tile')
import reference_tile as core
from fixtures import frame,capture,add_defect,STYLES
original=core.integer_difference

def transform(a,r):
    a=a.astype(np.int32);R,G,B=np.moveaxis(a,-1,0)
    y=(R+2*G+B+2)>>2;co=(R-B+256)>>1;cg=(-R+2*G-B+512)>>2
    def mean(v):return np.rint(core._mean(v,r)).astype(np.int32) if r else v
    return np.stack([y,mean(co),mean(cg)],axis=-1).astype(np.uint8)

rows=[]
for radius in (0,1,2,3):
    def difference(ref,cur,g,b,e,high=18,low=9):
        n,_,_,_=original(ref,cur,g,b,e,high,low)
        _,s,h,l=original(transform(ref,radius),transform(n,radius),[256]*3,[0]*3,e,high,low)
        return n,s,h,l
    core.integer_difference=difference
    for style in STYLES:
        ref=frame(style)
        for defect in (False,True):
            cur,truth=add_defect(ref,width=1) if defect else (ref,np.zeros((500,500),bool))
            r,m,_=core.compare(ref,capture(cur,jpeg=92))
            row=dict(radius=radius,style=style,defect=defect,status=r['status'],alarm=r['alarm'],reason=r.get('reason'),tp=int((m&truth).sum()) if m is not None else 0,truth=int(truth.sum()),regions=r.get('regions'),registration=r['registration'])
            rows.append(row);print(json.dumps(row),flush=True)
Path(__file__).with_name('probe_chroma.json').write_text(json.dumps(rows,indent=2))
