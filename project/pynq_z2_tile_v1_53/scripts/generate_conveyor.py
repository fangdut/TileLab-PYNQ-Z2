"""Deterministic engineering stimulus: indexed conveyor, never a real factory recording."""
from pathlib import Path
import json,sys,subprocess,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'host/_deps'))
import imageio_ffmpeg
W,H=1280,720;FPS=60;TW,TH=560,500
out=ROOT/'data/conveyor';out.mkdir(exist_ok=True)
rng=np.random.default_rng(20260923)
tiles=[]
for k in range(4):
 a=np.clip(195+rng.normal(0,1.0,(TH,TW)),0,255).astype(np.uint8)
 tile=Image.fromarray(np.stack([a,np.clip(a.astype(int)-3,0,255).astype('uint8'),np.clip(a.astype(int)-8,0,255).astype('uint8')],-1))
 d=ImageDraw.Draw(tile);truth=Image.new('L',(TW,TH));td=ImageDraw.Draw(truth)
 if k in (1,3):
  points=[(270,68),(265,103),(282,142),(260,180),(274,218),(249,255),(265,293),(254,332),(277,386),(269,431)]
  d.line(points,fill=(65,62,57),width=3 if k==1 else 6);td.line(points,fill=255,width=3 if k==1 else 6)
  pts=[points[4],(319,241),(346,279),(380,297)]
  d.line(pts,fill=(70,67,62),width=2);td.line(pts,fill=255,width=2)
 if k==2:
  d.ellipse((68,147,228,323),fill=(226,223,218))
 tile.save(out/f'tile_{k}.png');truth.save(out/f'tile_{k}_truth.png');tiles.append(tile)
def frame(k,phase):
 im=Image.new('RGB',(W,H),(30,39,44));d=ImageDraw.Draw(im)
 # Rails and rollers are intentionally outside the configured inspection ROI.
 d.rectangle((0,62,W,84),fill=(79,97,103));d.rectangle((0,636,W,658),fill=(79,97,103))
 for x in range(-100,1380,80):
  xx=(x+int(phase*45))%1440-80;d.rectangle((xx,92,xx+8,627),fill=(37,47,52))
 if phase<1.5:tx=int(-TW+(360+TW)*phase/1.5)
 elif phase<6.5:tx=360
 else:tx=int(360+(W-360)*(phase-6.5)/1.5)
 d.rounded_rectangle((tx-5,106,tx+TW+5,TH+118),radius=7,fill=(18,24,26))
 im.paste(tiles[k],(tx,110))
 d.text((25,24),f'SYNTHETIC HDMI INPUT   |   TILE {k+1:02d}   |   INDEXED CONVEYOR',fill=(183,204,205))
 d.text((25,684),'No detection boxes in source. All output boxes must come from the FPGA.',fill=(167,187,190))
 return im,tx
exe=imageio_ffmpeg.get_ffmpeg_exe();dest=ROOT/'data/conveyor_SYNTHETIC_720p60.mp4'
err=open(ROOT/'reports/conveyor_encode.log','wb')
p=subprocess.Popen([exe,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','-',
 '-an','-c:v','libx264','-preset','veryfast','-crf','14','-pix_fmt','yuv420p',str(dest)],stdin=subprocess.PIPE,stderr=err)
meta=[]
for k in range(4):
 for n in range(8*FPS):
  im,x=frame(k,n/FPS);p.stdin.write(im.tobytes())
  meta.append(dict(frame=k*8*FPS+n,tile=k+1,tile_x=x,tile_y=110,has_crack=k in (1,3),stationary=1.5<=n/FPS<6.5))
 im,_=frame(k,3);im.save(out/f'station_{k}.png');im.save(out/f'station_{k}.bmp')
p.stdin.close();assert p.wait()==0;err.close()
(out/'timeline.json').write_text(json.dumps(dict(provenance='PROCEDURAL_SYNTHETIC',fps=FPS,frames=meta),indent=2))
print(dest)
