"""Real photos, synthetic constant motion: never claim physical factory video."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,sys,subprocess
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'));import imageio_ffmpeg
D=R/'data/real_tiles';m=json.loads((D/'manifest.json').read_text())['samples']
good=[s for s in m if s['split']=='test' and s['label']=='good']
crack=[s for s in m if s['split']=='test' and s['label']=='crack']
chosen=[good[0],crack[0],good[1],crack[1]]
tiles=[Image.open(D/s['image']).convert('RGB').resize((500,500),Image.Resampling.BILINEAR) for s in chosen]
dest=R/'data/continuous_real_video_720p60.mp4';timeline=[]
with open(R/'reports/v14/encode_real_video.log','wb') as log:
 p=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','12','-pix_fmt','yuv420p',str(dest)],stdin=subprocess.PIPE,stderr=log)
 for n in range(720):
  im=Image.new('RGB',(1280,720),(30,39,44));d=ImageDraw.Draw(im);visible=[]
  for k,tile in enumerate(tiles):
   x=(n*8-k*1440+500)%5760-500
   if x<1280 and x+500>0:im.paste(tile,(x,110));visible.append(dict(id=chosen[k]['id'],label=chosen[k]['label'],x=x))
  d.text((24,23),f'MVTec AD | REAL PHOTOS / SYNTHETIC MOTION | 480 px/s | frame {n:04d}',fill=(210,220,225))
  d.text((24,682),'MVTec Software GmbH | CC BY-NC-SA 4.0 | Textured good tiles are a known false-positive case',fill=(210,220,225))
  for b in range(16):d.rectangle((1016+b*14,20,1027+b*14,39),fill='white' if n&(1<<b) else 'black')
  p.stdin.write(im.tobytes());timeline.append(dict(frame=n,visible=visible))
 p.stdin.close();assert p.wait()==0
(D/'video_manifest.json').write_text(json.dumps(dict(provenance='REAL_PHOTO_SYNTHETIC_MOTION',license='CC BY-NC-SA 4.0',source='https://www.mvtec.com/research-teaching/datasets/mvtec-ad',velocity_pixels_s=480,fps=60,stationary_frames=0,items=chosen,timeline=timeline),indent=2))
print('Real-photo composite motion video generated; known texture false positives disclosed')
