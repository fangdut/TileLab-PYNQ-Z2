"""Independent NumPy raster oracle: native RBG color, frame commits and masks."""
from pathlib import Path
import sys,json,zlib,numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from weak_reference import grow
O=R/'test_patterns/quad_integrated';O.mkdir(parents=True,exist_ok=True)
W,H,N=64,48,24;y,x=np.indices((H,W));rng=np.random.default_rng(124)
a=np.full((H,W),220,dtype=np.int32)
a[14:34,24:30]=rng.integers(70,176,(20,6))
a[18:23,14:48]=rng.integers(80,177,(5,34))
a[10,12]=30;a[30:33,40:43]=95
red=np.clip(a+15,0,255);green=np.clip(a-5,0,255);blue=np.clip(a-10,0,255)
native=(red<<16)|(blue<<8)|green
gray=(77*red+150*green+29*blue)>>8;score=valley(gray)
roi=(x>=W//5)&(x<=3*W//5)&(y>=H//4)&(y<=3*H//4)
def mem(name,values):
 (O/name).write_text('\n'.join(f'{int(v):08x}' for v in np.asarray(values).ravel())+'\n')
mem('input.mem',native);rows=[];brightness=[];allmasks=[]
for k in range(N):
 passes=4 if k%2 else 2;t=[89,90,255,0,70,110][k//4];en=k%4>=2
 mode=[6,6,7,0,4,5][k%6];keep=roi if en else np.ones_like(roi)
 strong=(score>t)&keep;weak=(score>(t+1)//2)&keep
 mask=strong.copy();first=None
 for j in range(passes):
  mask=grow(mask,weak,3);mask[[0,-1],:]=0;mask[:,[0,-1]]=0
  if j==0:first=mask.copy()
 mask&=keep
 cfg=((k%2==0)<<31)|mode|(t<<8)|(3<<16)|(int(en)<<20)|(1<<23)|(1<<24)|(int(passes==4)<<25)
 rgb=native.copy()
 if mode==4:rgb=strong.astype(np.uint32)*0xffffff
 if mode==5:rgb=(first&keep).astype(np.uint32)*0xffffff
 if mode==6:rgb=mask.astype(np.uint32)*0xffffff
 if mode==7:rgb=np.where(mask,0xff0000,native)
 mem(f'expected{k}.mem',rgb);yy,xx=np.where(mask);n=int(mask.sum())
 lo=int((int(yy.min())<<16)|int(xx.min())) if n else 0
 hi=int((int(yy.max())<<16)|int(xx.max())) if n else 0
 alarm=n>=32 and max((hi&65535)-(lo&65535),(hi>>16)-(lo>>16))>=23
 rows.append(dict(frame=k,config=int(cfg),count=n,lo=lo,hi=hi,status=(3 if n else 1)|(4 if alarm else 0),crc=zlib.crc32(np.packbits(mask.ravel(),bitorder='little').tobytes()),passes=passes))
 brightness.append(dict(count=int(keep.sum()),total=int(gray[keep].sum())));allmasks.append(mask)
assert np.any(allmasks[0]!=allmasks[1]),'Test must distinguish two/four passes'
mem('config.mem',[v['config'] for v in rows])
for key in ('config','count','lo','hi','status','crc'):mem('stats_'+key+'.mem',[v[key] for v in rows]+[0])
for key in ('count','total'):mem('brightness_'+key+'.mem',[v[key] for v in brightness]+[0])
(O/'metadata.json').write_text(json.dumps(dict(frames=rows,native_order='RBG',different_two_four_pixels=int((allmasks[0]!=allmasks[1]).sum())),indent=2))
s=(R/'sim/tb_quad_legacy_detection.sv').read_text().replace('tb_quad_legacy_detection','tb_quad_integrated').replace('FRAMES=30','FRAMES=24').replace('W=32,H=20,HT=200,VT=50,TOP=10','W=64,H=48,HT=200,VT=90,TOP=20')
s=s.replace('30 configurations including PL local contrast, morphology bypass, PL alarm and red bbox, threshold equality/extremes, open/close, ROI, four legacy modes','24 configurations: two/four passes, colored RBG pixels, threshold extremes, ROI and per-frame commits')
(R/'sim/tb_quad_integrated.sv').write_text(s)
s=(R/'scripts/test_quad_legacy.tcl').read_text().replace('tb_quad_legacy_detection','tb_quad_integrated')
(R/'scripts/test_quad_integrated.tcl').write_text(s)
print(f'{N*W*H} exact colored pixels; two/four distinction {(allmasks[0]!=allmasks[1]).sum()} pixels')
