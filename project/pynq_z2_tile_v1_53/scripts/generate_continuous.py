"""Constant-velocity conveyor; no dwell. Source barcodes are validation only."""
from pathlib import Path
import subprocess,json,sys
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'))
import imageio_ffmpeg
out=R/'data/conveyor';tiles=[Image.open(out/f'tile_{i}.png').convert('RGB') for i in range(4)]
W,H=1280,720;TW,TH=560,500;pitch=1440;period=4*pitch
def render(n,step):
 im=Image.new('RGB',(W,H),(30,39,44));d=ImageDraw.Draw(im)
 d.rectangle((0,62,W,84),fill=(79,97,103));d.rectangle((0,636,W,658),fill=(79,97,103))
 for base in range(-80,1360,80):
  xx=base+(n*step)%80;d.rectangle((xx,92,xx+8,627),fill=(37,47,52))
 visible=[]
 for k,tile in enumerate(tiles):
  tx=(n*step-k*pitch+TW)%period-TW
  if tx<W and tx+TW>0:
   d.rectangle((tx-5,106,tx+TW+5,618),fill=(18,24,26));im.paste(tile,(tx,110));visible.append(dict(tile=k+1,x=tx,crack=k in (1,3)))
 d.text((24,23),f'SYNTHETIC CONTINUOUS CONVEYOR  |  {step*60} px/s  |  FRAME {n:04d}',fill=(190,210,212))
 d.text((24,683),'Constant speed; no stop under camera. Detection boxes are generated only by FPGA.',fill=(167,187,190))
 # 16 little-endian binary cells outside inspection ROI. Compress robustly.
 for b in range(16):d.rectangle((1016+b*14,20,1027+b*14,39),fill='white' if n&(1<<b) else 'black')
 return im,visible
exe=imageio_ffmpeg.get_ffmpeg_exe();manifest=[]
for name,step in [('video',8),('fast',16),('ultrafast',32)]:
 frames=period//step;dest=R/'data'/f'continuous_{name}_720p60.mp4'
 with open(R/'reports/v14'/f'encode_{name}.log','wb') as log:
  p=subprocess.Popen([exe,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','12','-pix_fmt','yuv420p',str(dest)],stdin=subprocess.PIPE,stderr=log)
  timeline=[]
  for n in range(frames):
   im,v=render(n,step);p.stdin.write(im.tobytes());timeline.append(dict(frame=n,visible=v))
  p.stdin.close();assert p.wait()==0
 manifest.append(dict(name=name,file=str(dest.relative_to(R)),fps=60,velocity_pixels_s=step*60,product_pitch_pixels=pitch,inspection_scope='one product visible while center gate is occupied; fixed spacing, no speed pauses',frames=frames,stationary_frames=0,timeline=timeline))
empty=Image.new('RGB',(W,H),(30,39,44));empty.save(out/'station_6.png')
(out/'continuous_timeline.json').write_text(json.dumps(dict(provenance='PROCEDURAL_SYNTHETIC',videos=manifest),indent=2),encoding='utf-8')
print('Generated constant-motion videos at 480, 960 and 1920 pixels/second')
