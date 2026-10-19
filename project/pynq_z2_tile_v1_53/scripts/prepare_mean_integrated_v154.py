"""Independent NumPy raster oracle: native RBG color, frame commits and masks."""
from pathlib import Path
import sys,json,zlib,argparse,numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from weak_reference import grow
from directional_mean_reference import directional_mean_score
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=R/'reports/v154/mean_integrated_vectors');args=ap.parse_args()
O=args.out;O.mkdir(parents=True,exist_ok=False)
W,H,N=96,80,64;y,x=np.indices((H,W));rng=np.random.default_rng(152)
a=np.full((H,W),220,dtype=np.int32)
a[14:34,24:30]=rng.integers(70,176,(20,6))
a[18:23,14:48]=rng.integers(80,177,(5,34))
a[10,12]=30;a[30:33,40:43]=95
a[20:64,36:59]=150;a[27:56,42:47]=75
red=np.clip(a+15,0,255);green=np.clip(a-5,0,255);blue=np.clip(a-10,0,255)
native=(red<<16)|(blue<<8)|green
gray=(77*red+150*green+29*blue)>>8;score=valley(gray);wide=valley(gray,16)
mean_short=directional_mean_score(gray,8);mean_long=directional_mean_score(gray,16)
roi=(x>=W//5)&(x<=3*W//5)&(y>=H//4)&(y<=3*H//4)
def mem(name,values):
 (O/name).write_text('\n'.join(f'{int(v):08x}' for v in np.asarray(values).ravel())+'\n')
mem('input.mem',native);rows=[];brightness=[];allmasks=[]
for k in range(N):
 passes=4 if k%2 else 2;t=[90,255,0,70][k//16];en=k%8>=4;wide_on=k%4>=2
 ridge_on=k%16>=8
 mode=[6,6,7,0,4,5][k%6];keep=roi if en else np.ones_like(roi)
 strong=(score>t)&keep;weak=((np.maximum(score,wide) if wide_on else score)>(t+1)//2)&keep
 if ridge_on:
  strong|=((mean_short>40)|(mean_long>48))&keep
  weak|=((mean_short>20)|(mean_long>24))&keep
 mask=strong.copy();first=None
 for j in range(passes):
  mask=grow(mask,weak,3);mask[[0,-1],:]=0;mask[:,[0,-1]]=0
  if j==0:first=mask.copy()
 mask&=keep
 cfg=((k%2==0)<<31)|mode|(t<<8)|(3<<16)|(int(en)<<20)|(1<<23)|(1<<24)|(int(passes==4)<<25)|(int(wide_on)<<27)|(int(ridge_on)<<28)
 rgb=native.copy()
 if mode==4:rgb=strong.astype(np.uint32)*0xffffff
 if mode==5:rgb=(first&keep).astype(np.uint32)*0xffffff
 if mode==6:rgb=mask.astype(np.uint32)*0xffffff
 if mode==7:rgb=np.where(mask,0xff0000,native)
 mem(f'expected{k}.mem',rgb);yy,xx=np.where(mask);n=int(mask.sum())
 lo=int((int(yy.min())<<16)|int(xx.min())) if n else 0
 hi=int((int(yy.max())<<16)|int(xx.max())) if n else 0
 alarm=n>=32 and max((hi&65535)-(lo&65535),(hi>>16)-(lo>>16))>=23
 rows.append(dict(frame=k,config=int(cfg),count=n,lo=lo,hi=hi,status=(3 if n else 1)|(4 if alarm else 0),crc=zlib.crc32(np.packbits(mask.ravel(),bitorder='little').tobytes()),passes=passes,wide=wide_on))
 brightness.append(dict(count=int(keep.sum()),total=int(gray[keep].sum())));allmasks.append(mask)
assert np.any(allmasks[0]!=allmasks[8]),'Test must distinguish directional mean on/off'
assert np.any(allmasks[0]!=allmasks[1]),'Test must distinguish two/four passes'
assert np.any(allmasks[1]!=allmasks[3]),'Test must distinguish wide on/off'
mem('config.mem',[v['config'] for v in rows])
for key in ('config','count','lo','hi','status','crc'):mem('stats_'+key+'.mem',[v[key] for v in rows]+[0])
for key in ('count','total'):mem('brightness_'+key+'.mem',[v[key] for v in brightness]+[0])
(O/'metadata.json').write_text(json.dumps(dict(frames=rows,native_order='RBG',different_two_four_pixels=int((allmasks[0]!=allmasks[1]).sum()),different_wide_pixels=int((allmasks[1]!=allmasks[3]).sum())),indent=2))

print(f'{N*W*H} pixels, wide distinction {int((allmasks[1]!=allmasks[3]).sum())}')
