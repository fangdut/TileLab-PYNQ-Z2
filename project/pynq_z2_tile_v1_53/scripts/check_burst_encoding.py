from pathlib import Path
import sys,json,subprocess,numpy as np
r=Path(__file__).resolve().parents[1];sys.path[:0]=[str(r/'host/_deps'),str(r/'models')]
import imageio_ffmpeg
from valley_reference import detect
exe=imageio_ffmpeg.get_ffmpeg_exe();p=subprocess.Popen([exe,'-v','error','-i',str(r/'data/burst_SYNTHETIC_720p60.mp4'),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
rows=[];previous=False;events=0
for frame in range(1200):
 raw=p.stdout.read(1280*720*3)
 if len(raw)!=1280*720*3:raise ValueError('Incomplete decoded frame')
 # Verify every encoded frame, including normal periods for false alarms.
 a=np.frombuffer(raw,np.uint8).reshape(720,1280,3);_,v=detect(a)
 alarm=v['alarm'];events+=int(alarm and not previous);previous=alarm
 rows.append(dict(frame=frame,area=v['candidate_pixels'],alarm=alarm))
p.stdout.close();p.wait()
(r/'reports/encoded_burst_reference.json').write_text(json.dumps(dict(events=events,frames=rows),indent=2))
print('Encoded input reference events',events,flush=True)
