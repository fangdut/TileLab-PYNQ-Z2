"""Measure normal training photos through the actual video decode and HDMI path."""
from pathlib import Path
import sys,json,time,hashlib,io
import numpy as np
from PIL import Image
import board_v13_acceptance as t
from calibrate_v15_hdmi import samples,barcode,sha
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
OUT=R/'reports/v15/video_calibration';OUT.mkdir(parents=True,exist_ok=True)
t.action('pause')
while t.state()['busy']:time.sleep(.05)
t.action('display',value='station_6');time.sleep(.4)
while t.action('status')['depth']:t.shot()
t.action('threshold',value=105)
for _ in range(6):
 warm=t.shot()
 if ((warm['frame']['config_word']>>8)&255)==105:break
else:raise AssertionError('Calibration threshold did not settle on empty belt')
before=t.action('status');rows={};t.action('display',value='calib_video');deadline=time.monotonic()+330
while len(rows)<230:
 if time.monotonic()>deadline:raise TimeoutError(f'Only {len(rows)}/230 training identities captured')
 st=t.shot();raw=t.get('/api/image');im=Image.open(io.BytesIO(raw)).convert('RGB');code=barcode(im)
 if not 1<=code<=230 or code in rows:continue
 n=code-1;s=samples[n];(OUT/f'calib_{n:03d}.png').write_bytes(raw)
 a=np.asarray(im,dtype=np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
 score=valley(gray)[80:640,80:1200];critical=int(np.partition(score.ravel(),-32)[-32])
 rows[code]=dict(index=n,id=s['id'],split='train',label='good',critical_score=critical,captured_sha256=sha(raw),source_sha256=sha((R/'data/real_tiles'/s['image']).read_bytes()),frame_id=st['frame']['frame_id'],boot_id=st['frame']['boot_id'])
 (OUT/'progress.json').write_text(json.dumps(list(rows.values()),indent=2))
 if len(rows)%20==0:print(json.dumps(dict(captured=len(rows),path='H264_VIDEO_HDMI',normal_training_only=True)),flush=True)
t.action('display',value='station_6');time.sleep(.4)
while t.action('status')['depth']:t.shot()
after=t.action('status');t.action('disconnect');ordered=[rows[k] for k in sorted(rows)]
threshold=int(np.percentile([r['critical_score'] for r in ordered],99,method='higher'))
assert 1<=threshold<=255 and all(after[k]==before[k] for k in ('gaps','invalid','dropped'))
result=dict(method='Same 99th percentile higher / per-normal-training-photo 32nd highest score; actual H264 playback and HDMI capture; no test labels used',threshold=threshold,normal_training_count=230,scope='Current WPF H264 video decode and PC display color pipeline, 500px MVTec tile photos. Recalibrate when source/camera/display/material changes.',before=before,after=after,items=ordered)
path=OUT/'calibration.json';path.write_text(json.dumps(result,indent=2))
recipe=dict(id='mvtec_video_v15',name='本机视频链路纹理瓷砖标定',threshold=threshold,description='230 张正常训练图经实际视频解码和 HDMI 链路标定；用于当前真实照片运动视频',scope=result['scope'],calibration_sha256=sha(path.read_bytes()))
catalog=json.loads((R/'host/recipes.json').read_text(encoding='utf-8'));catalog['recipes']=[r for r in catalog['recipes'] if r['id']!='mvtec_video_v15']+[recipe]
(R/'host/recipes.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(threshold=threshold,captured=230,recipe_id=recipe['id'])),flush=True)
