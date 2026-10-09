"""Decode across each file's internal repeat boundary; verify frame continuity."""
from pathlib import Path
import sys,subprocess,json
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'));import imageio_ffmpeg
rows=[]
for m in json.loads((R/'data/conveyor/long_stream_manifest.json').read_text())['streams']:
 n=m['source_cycle_frames'];p=R/m['file']
 cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(p),'-vf',f'select=between(n\\,{n-2}\\,{n+1})','-vsync','0','-frames:v','4','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
 raw=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
 a=np.frombuffer(raw,np.uint8).reshape(4,720,1280,3)
 codes=[sum(int(im[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16)) for im in a]
 row=dict(mode=m['mode'],barcodes=codes,expected=[n-2,n-1,0,1],passed=codes==[n-2,n-1,0,1]);rows.append(row)
 assert row['passed'],row
(R/'reports/v14/long_stream_validation.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
