"""Legacy coverage plus fixed-profile guards; integer oracle, native RBG input."""
from pathlib import Path
import argparse,runpy,sys,json,zlib
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from support_profiles_v155 import compute_features,DIRECTIONS
from weak_reference import grow
from ridge_reference import shifted
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
sys.argv=[str(R/'scripts/prepare_mean_integrated_v154.py'),'--out',str(args.out)]
v=runpy.run_path(sys.argv[0]);O=args.out;W=v['W'];H=v['H'];native=v['native'];gray=v['gray'];roi=v['roi'];mem=v['mem'];rows=v['rows'];brightness=v['brightness'];masks=v['allmasks']
n,w,s,l,line,dirs=compute_features(gray)
for k in range(64,112):
 j=k-64;profile=j%6;t=89 if profile==4 else 90
 cb=profile in (0,2,3,4,5);db=profile in (1,2)
 ridge=profile!=3;wide=profile!=5
 active=ridge and wide and t==90 and not(cb and db)
 conservative=cb and active;sensitive=db and active
 keep=roi if (j//6)%2 else np.ones_like(roi);mode=[6,7,4,5][j//12]
 seed=((n>t)|(((s>40)|(l>48)) if ridge else False))&keep
 weak=((np.maximum(n,w) if wide else n)>(t+1)//2)&keep
 if ridge:weak|=((s>20)|(l>24))&keep
 if conservative:seed|=(line>60)&keep;weak|=(line>30)&keep
 mask=seed.copy();first=None;passes=8 if sensitive else 4
 for stage in range(passes):
  result=grow(mask,weak,3)
  if sensitive:
   for eligible,(dx,dy) in zip(dirs&keep,DIRECTIONS):result|=eligible&(shifted(mask,dx,dy)|shifted(mask,-dx,-dy))
  mask=result;mask[[0,-1],:]=0;mask[:,[0,-1]]=0
  if stage==0:first=mask.copy()
 mask&=keep
 cfg=((k%2==0)<<31)|mode|(t<<8)|(3<<16)|(int(keep is roi)<<20)|(1<<23)|(1<<24)|(1<<25)|(int(wide)<<27)|(int(ridge)<<28)|(int(cb)<<29)|(int(db)<<30)
 rgb=mask.astype(np.uint32)*0xffffff if mode==6 else np.where(mask,0xff0000,native) if mode==7 else seed.astype(np.uint32)*0xffffff if mode==4 else (first&keep).astype(np.uint32)*0xffffff
 mem(f'expected{k}.mem',rgb);yy,xx=np.where(mask);count=int(mask.sum())
 lo=int((int(yy.min())<<16)|int(xx.min())) if count else 0;hi=int((int(yy.max())<<16)|int(xx.max())) if count else 0
 alarm=count>=32 and max((hi&65535)-(lo&65535),(hi>>16)-(lo>>16))>=23
 rows.append(dict(frame=k,config=int(cfg),count=count,lo=lo,hi=hi,status=(3 if count else 1)|(4 if alarm else 0),crc=zlib.crc32(np.packbits(mask.ravel(),bitorder='little').tobytes()),passes=passes,conservative=conservative,sensitive=sensitive))
 brightness.append(dict(count=int(keep.sum()),total=int(gray[keep].sum())));masks.append(mask)
assert (masks[64]!=masks[65]).any(),'New operating points must be distinguished'
for k in range(112,128):
 j=k-112;closing=bool(j&1);raw=bool(j&2);keep=roi if j&4 else np.ones_like(roi);mode=[6,7,4,5][j//4]
 seed=(n>90)&keep
 def morph(a,dilate):
  stack=np.stack([shifted(a,dx,dy) for dy in [-1,0,1] for dx in [-1,0,1]])
  result=stack.any(axis=0) if dilate else stack.all(axis=0)
  result[[0,-1],:]=False;result[:,[0,-1]]=False;return result
 first=morph(seed,closing);mask=(seed if raw else morph(first,not closing))&keep
 cfg=((k%2==0)<<31)|mode|(90<<8)|(3<<16)|(int(closing)<<18)|(int(keep is roi)<<20)|(int(raw)<<22)|(1<<23)
 rgb=mask.astype(np.uint32)*0xffffff if mode==6 else np.where(mask,0xff0000,native) if mode==7 else seed.astype(np.uint32)*0xffffff if mode==4 else (first&keep).astype(np.uint32)*0xffffff
 mem(f'expected{k}.mem',rgb);yy,xx=np.where(mask);count=int(mask.sum());lo=int((int(yy.min())<<16)|int(xx.min())) if count else 0;hi=int((int(yy.max())<<16)|int(xx.max())) if count else 0
 alarm=count>=32 and max((hi&65535)-(lo&65535),(hi>>16)-(lo>>16))>=23
 rows.append(dict(frame=k,config=int(cfg),count=count,lo=lo,hi=hi,status=(3 if count else 1)|(4 if alarm else 0),crc=zlib.crc32(np.packbits(mask.ravel(),bitorder='little').tobytes()),passes=0,closing=closing,raw=raw))
 brightness.append(dict(count=int(keep.sum()),total=int(gray[keep].sum())));masks.append(mask)
mem('config.mem',[r['config'] for r in rows])
for key in ('config','count','lo','hi','status','crc'):mem('stats_'+key+'.mem',[r[key] for r in rows]+[0])
for key in ('count','total'):mem('brightness_'+key+'.mem',[r[key] for r in brightness]+[0])
(O/'metadata.json').write_text(json.dumps(dict(frames=rows,pixels=128*W*H,scope='64 legacy growth, 48 profile/ROI/display/guard combinations, 16 opening/closing/raw cases; RGB/sync, count/bbox, brightness and CRC',native_order='RBG',different_profile_pixels=int((masks[64]!=masks[65]).sum())),indent=2))
print('128 configurations:',128*W*H,'pixels')
