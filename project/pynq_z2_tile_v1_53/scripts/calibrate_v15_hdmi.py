"""Calibrate only from normal training photographs captured through actual HDMI.
No test labels are read. Numeric rule matches the source-space calibration.
"""
from pathlib import Path
import sys,json,time,hashlib,argparse,io
import numpy as np
from PIL import Image,ImageOps,ImageDraw
import board_v13_acceptance as t
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
OUT=R/'reports/v15/hdmi_calibration';OUT.mkdir(exist_ok=True,parents=True)
SOURCE=R/'data/calibration_hdmi';SOURCE.mkdir(exist_ok=True)
samples=[s for s in json.loads((R/'data/real_tiles/manifest.json').read_text())['samples'] if s['split']=='train']
assert len(samples)==230 and all(s['label']=='good' for s in samples)
def sha(b):return hashlib.sha256(b).hexdigest()
def barcode(im):
 a=np.asarray(im);return sum(int(a[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))
def prepare():
 for n,s in enumerate(samples):
  p=SOURCE/f'calib_{n:03d}.png'
  photo=ImageOps.exif_transpose(Image.open(R/'data/real_tiles'/s['image'])).convert('RGB');photo.thumbnail((500,500),Image.Resampling.BILINEAR)
  im=Image.new('RGB',(1280,720),(30,39,44));im.paste(photo,((1280-photo.width)//2,(720-photo.height)//2));draw=ImageDraw.Draw(im)
  for bit in range(16):draw.rectangle((1018+bit*14,22,1024+bit*14,37),fill='white' if ((n+1)>>bit)&1 else 'black')
  im.save(p)
 print('Prepared 230 normal-training HDMI scenes with frame identity outside ROI',flush=True)
def acquire():
 t.action('pause')
 while t.state()['busy']:time.sleep(.05)
 t.action('display',value='station_6');time.sleep(.4)
 while t.action('status')['depth']:t.shot()
 before=t.action('status');rows=[]
 for n,s in enumerate(samples):
  command=f'calib_{n:03d}';t.action('display',value=command)
  deadline=time.monotonic()+4
  while True:
   player=json.loads((R/'host/player_status.json').read_text(encoding='utf-8-sig'))
   if player['source']==command:break
   if time.monotonic()>deadline:raise TimeoutError(command)
   time.sleep(.025)
  for _ in range(4):
   st=t.shot();raw=t.get('/api/image');im=Image.open(io.BytesIO(raw)).convert('RGB')
   if barcode(im)==n+1:break
  else:raise AssertionError('Captured training identity does not match '+command)
  (OUT/f'{command}.png').write_bytes(raw)
  a=np.asarray(im,dtype=np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
  score=valley(gray)[80:640,80:1200];critical=int(np.partition(score.ravel(),-32)[-32])
  rows.append(dict(index=n,id=s['id'],split='train',label='good',critical_score=critical,captured_sha256=sha(raw),source_sha256=sha((R/'data/real_tiles'/s['image']).read_bytes()),frame_id=st['frame']['frame_id'],boot_id=st['frame']['boot_id']))
  (OUT/'progress.json').write_text(json.dumps(rows,indent=2))
  if (n+1)%20==0:print(json.dumps(dict(captured=n+1,normal_training_only=True)),flush=True)
 t.action('display',value='station_6');time.sleep(.4)
 while t.action('status')['depth']:t.shot()
 after=t.action('status');t.action('disconnect')
 threshold=int(np.percentile([r['critical_score'] for r in rows],99,method='higher'))
 assert 1<=threshold<=255 and all(after[k]==before[k] for k in ('gaps','invalid','dropped'))
 result=dict(method='99th percentile higher of each captured normal-training frame 32nd highest opposed-valley score; numeric rule unchanged; no test labels used',threshold=threshold,normal_training_count=len(rows),source_space_threshold=105,scope='Current PC display color pipeline to PYNQ HDMI at 500px photo scale. Recalibrate after changes to display profile, camera, material, lighting or scale.',before=before,after=after,items=rows)
 path=OUT/'calibration.json';path.write_text(json.dumps(result,indent=2))
 recipe=dict(id='mvtec_hdmi_v15',name='本机 HDMI 纹理瓷砖标定',threshold=threshold,description='230 张正常训练图经当前 HDMI 链路实采标定；更换显示色彩设置或相机后需重新标定',scope=result['scope'],calibration_sha256=sha(path.read_bytes()))
 catalog=json.loads((R/'host/recipes.json').read_text(encoding='utf-8'));catalog['recipes']=[r for r in catalog['recipes'] if r['id']!='mvtec_hdmi_v15']+[recipe]
 (R/'host/recipes.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(threshold=threshold,captured=len(rows),recipe_id=recipe['id'])),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args();prepare()
 if not args.prepare_only:acquire()
