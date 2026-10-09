from pathlib import Path
import numpy as np,json,sys,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models'))
from valley_reference import valley
from regions_reference import regions
r=Path(__file__).resolve().parent.parent/'test_patterns';r.mkdir(exist_ok=True);w=int(sys.argv[1]) if len(sys.argv)>1 else 32;h=int(sys.argv[2]) if len(sys.argv)>2 else 20
out=r/f'quad_legacy_grid_{w}';out.mkdir(exist_ok=True)
y,x=np.indices((h,w));a=np.zeros((h,w),np.int32)
a[(x>w//8)&(x<w//3)&(y>h//5)&(y<4*h//5)]=255
a[(x>w//2)&(x<7*w//8)&(y>h//4)&(y<3*h//4)]=200
a[(x==w//4)&(y==h//2)]=0 # hole
a[(x==w//2)&(y==h//7)]=255 # isolated white dot
a[(x>3*w//4)&(y<h//8)]=80
a[(x==0)|(y==0)|(x==w-1)|(y==h-1)]=255 # hostile border
if len(sys.argv)>3 and sys.argv[3]=='tile':
 a=(170+30*x//w).astype(np.int32)
 a[h//6:5*h//6,w//3]=40
 a[h//2:h//2+2,w//5:4*w//5]=65
 for dy in range(h//4,3*h//4):
  dx=w//2+dy//2;a[dy,dx:dx+3]=55
def conv(a,k):
 s=np.zeros((h-2,w-2),np.int32)
 for j in range(3):
  for i in range(3):s+=a[j:j+h-2,i:i+w-2]*k[j][i]
 out=np.zeros((h,w),np.int32);out[1:-1,1:-1]=s;return out
smooth=conv(a,[[1,2,1],[2,4,2],[1,2,1]])//16
edge=np.minimum(abs(conv(a,[[-1,0,1],[-2,0,2],[-1,0,1]]))+abs(conv(a,[[-1,-2,-1],[0,0,0],[1,2,1]])),255)
def morph(b,dilate):return np.where(conv(b.astype(np.int32),[[1]*3]*3)>0 if dilate else conv(b.astype(np.int32),[[1]*3]*3)==9,1,0)
configs=[]
for mode in range(8):configs.append((mode,100,0,0,False))
configs += [(6,100,0,1,False),(6,100,0,0,True),(4,255,0,0,False),(6,100,1,0,False),(4,80,0,0,False),(6,100,2,1,True)]
configs=[(*v,0,0) for v in configs]
configs += [(4,80,0,0,False,1,0),(6,100,0,0,True,1,0),(6,100,1,1,True,1,0),
            (7,100,0,0,True,0,1),(7,100,0,0,True,0,1),(7,100,0,0,True,0,1),
            (7,255,0,0,True,0,1),(7,255,0,0,True,0,1)]
configs=[(*v,0) for v in configs]
configs += [(4,12,3,0,False,0,0,1),(6,12,3,0,False,0,0,1),(6,12,3,0,True,0,0,1),
            (7,12,3,0,False,0,1,1),(7,12,3,0,False,0,1,1),(6,12,3,1,True,0,0,0),
            (4,255,3,0,False,0,0,1),(4,0,3,0,False,1,0,1)]

def mem(path,data):path.write_text('\n'.join(f'{int(v):06x}' for v in data.ravel())+'\n')
mem(out/'input.mem',a*0x010101)
roi=(x>=w//5)&(x<=3*w//5)&(y>=h//4)&(y<=3*h//4)
meta=[];brightness=[];previous_mask=None;previous_cfg=None
for n,(mode,t,src,close,en,dark,box,bypass) in enumerate(configs):
 brightness.append(dict(count=int(roi.sum()) if en else w*h,total=int(a[roi].sum()) if en else int(a.sum())))
 srcim=[a,smooth,edge,valley(a)][src];mask=(srcim<t if dark and src!=3 else srcim>t)&(roi if en else True)
 s1=morph(mask,close);s2=morph(s1,not close)
 if en:s1*=roi;s2*=roi
 if bypass:s2=mask.astype(np.int32)
 if mode<4:rgb=[a,a,edge,smooth][mode]*0x010101
 elif mode<7:rgb=[mask,s1,s2][mode-4].astype(np.int32)*0xffffff
 else:rgb=a*0x010101 if box else np.where(s2,0xff0000,a*0x010101)
 cfg=((~previous_cfg)&0x80000000 if previous_cfg is not None else 0x80000000)|mode|t<<8|src<<16|close<<18|dark<<19|en<<20|box<<21|bypass<<22|(int(src==3)<<23)
 if n in (18,19,21,26):cfg=previous_cfg
 # Current region_grid gates every source, including legacy display modes.
 # HDMI overlays the previous completed frame's grid components.
 if box and mode==7 and previous_mask is not None:
  for bx0,by0,bx1,by1 in regions(previous_mask)['boxes']:
   border=(((x==bx0)|(x==bx1))&(y>=by0)&(y<=by1))|(((y==by0)|(y==by1))&(x>=bx0)&(x<=bx1))
   rgb=np.where(border,0xff0000,rgb)
 previous_mask=s2.copy();previous_cfg=cfg
 mem(out/f'expected{n}.mem',rgb)
 yy,xx=np.where(s2)
 meta.append(dict(frame=n,crc=zlib.crc32(np.packbits(s2.ravel(),bitorder="little").tobytes()),config=int(cfg),count=int(s2.sum()),lo=int((int(yy.min())<<16)|int(xx.min())) if len(xx) else 0,hi=int((int(yy.max())<<16)|int(xx.max())) if len(xx) else 0))
mem(out/'config.mem',np.array([v['config'] for v in meta],np.uint32))
(out/'metadata.json').write_text(json.dumps(meta,indent=2))
# Different image after loss-of-lock reset exercises stale morphology line RAM.
b=(255-a)>100
rec=morph(morph(b,False),True)
mem(out/'recovery_input.mem',(255-a)*0x010101);mem(out/'recovery_expected.mem',rec*0xffffff)
yy,xx=np.where(rec)
meta.append(dict(frame=len(configs),crc=zlib.crc32(np.packbits(rec.ravel(),bitorder="little").tobytes()),config=0x80006406,count=int(rec.sum()),lo=int((int(yy.min())<<16)|int(xx.min())) if len(xx) else 0,hi=int((int(yy.max())<<16)|int(xx.max())) if len(xx) else 0))
for v in meta:
 v['status']=(3 if v['count'] else 1) | (4 if ((v['config']>>16)&3)==3 and v['count']>=32 and max((v['hi']&65535)-(v['lo']&65535),(v['hi']>>16)-(v['lo']>>16))>=23 else 0)
for key in ['count','lo','hi','config','crc','status']:mem(out/('stats_'+key+'.mem'),np.array([v[key] for v in meta],np.uint32))
(out/'metadata.json').write_text(json.dumps(meta,indent=2))
print(out)

brightness.append(dict(count=w*h,total=int((255-a).sum())))
for key in ['count','total']:mem(out/('brightness_'+key+'.mem'),np.array([v[key] for v in brightness],np.uint32))
