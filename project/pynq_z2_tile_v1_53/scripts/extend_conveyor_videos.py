"""Build 10-minute streams so short file replay never pauses a board soak."""
from pathlib import Path
import subprocess,sys,json,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'));import imageio_ffmpeg
rows=[]
for mode,period in [('video',12),('fast',6),('ultrafast',3),('real_video',12)]:
 src=R/f'data/continuous_{mode}_720p60.mp4';dst=src.with_name(f'continuous_{mode}_long_720p60.mp4')
 with (R/f'reports/v14/extend_{mode}.log').open('wb') as log:
  subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-stream_loop',str(600//period-1),'-i',str(src),'-map','0:v:0','-c','copy','-t','600','-movflags','+faststart',str(dst)],stdout=log,stderr=subprocess.STDOUT,check=True)
 rows.append(dict(mode=mode,file=str(dst.relative_to(R)),duration_seconds=600,fps=60,source_cycle_frames=period*60,sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
(R/'data/conveyor/long_stream_manifest.json').write_text(json.dumps(dict(purpose='Avoid 3/6/12 second MediaEnded decoder restarts during continuous tests; source barcodes remain cyclic.',streams=rows),indent=2))
print('Four 600-second videos generated')
