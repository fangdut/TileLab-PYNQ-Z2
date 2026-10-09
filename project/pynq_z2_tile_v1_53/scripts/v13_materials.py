from pathlib import Path
import json,sys,subprocess
import numpy as np
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parents[1];out=r/'data/conveyor';sys.path.insert(0,str(r/'host/_deps'))
import imageio_ffmpeg
normal=Image.open(out/'station_0.png').convert('RGB');two=normal.copy();d=ImageDraw.Draw(two)
d.line([(492,170),(480,215),(502,267),(487,312),(504,375),(488,440),(500,526)],fill=(60,57,52),width=4)
d.line([(791,216),(778,258),(794,309),(780,358),(800,403),(786,470),(803,554)],fill=(65,62,58),width=3)
two.save(out/'station_4.png');noise=normal.copy();d=ImageDraw.Draw(noise)
for x,y in [(430,180),(580,320),(730,450),(845,520)]:d.rectangle((x,y,x+2,y+2),fill=(60,57,52))
noise.save(out/'station_5.png')
exe=imageio_ffmpeg.get_ffmpeg_exe();log=open(r/'reports/burst_encode.log','wb')
proc=subprocess.Popen([exe,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','60','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','14','-pix_fmt','yuv420p',str(r/'data/burst_SYNTHETIC_720p60.mp4')],stdin=subprocess.PIPE,stderr=log)
timeline=[]
for n in range(1200):
 # Six-frame (100ms) appearances, with 400ms clean intervals; all sixteen
 # events occur before 9s, followed by 11s of normal input for stopping playback.
 alarm=60<=n<540 and (n-60)%30<6
 im=two.copy() if alarm else normal.copy();dr=ImageDraw.Draw(im)
 dr.rectangle((0,0,1279,55),fill=(30,39,44));dr.text((25,24),f'SYNTHETIC QUEUE STRESS  |  FRAME {n:04d}  |  NO SOURCE BOXES',fill=(183,204,205))
 proc.stdin.write(im.tobytes());timeline.append(int(alarm))
proc.stdin.close();assert proc.wait()==0;log.close()
(out/'burst_timeline.json').write_text(json.dumps(dict(provenance='PROCEDURAL_SYNTHETIC',fps=60,events=16,positive_frames_per_event=6,frames=timeline)))
print('Two-region, isolated-dot and 16 short-event video generated')
