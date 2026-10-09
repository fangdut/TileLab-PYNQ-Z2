from pathlib import Path
import sys,subprocess,json
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'));sys.path.insert(0,str(R/'models'))
import imageio_ffmpeg
from valley_reference import detect,valley
from regions_reference import regions
out=R/'reports/v15/video_source_diagnostic.png'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',str(R/'data/continuous_real_video_long_720p60.mp4'),'-vf',r'select=eq(n\,229)','-frames:v','1',str(out)],check=True)
im=Image.open(out);a=np.asarray(im,dtype=np.int32);g=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
result=dict(frame_index=229,roi_32nd_highest_score=int(np.partition(valley(g)[80:640,80:1200].ravel(),-32)[-32]),predictions={})
for t in (105,90,80):
 m,_=detect(im,threshold=t);result['predictions'][str(t)]=dict(candidates=int(m.sum()),**regions(m))
(R/'reports/v15/video_source_diagnostic.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
