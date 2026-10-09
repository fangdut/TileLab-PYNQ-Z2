"""Direct actual-board 50-photo regression; no auto-archive duplication."""
from pathlib import Path
import sys,json,time,io,argparse
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5'
sys.path[:0]=[str(R/'host'),str(R/'models')]
from workstation import EthernetBridge
from weak_reference import detect
from regions_reference import regions
import board_v13_acceptance as t
HIGH=90;PASSES=4;OUT=R/'reports/v132/real_board'
def empty(bridge):
 t.action('display',value='station_6');time.sleep(.35)
 for _ in range(20):
  f,im,mask=bridge.capture(HIGH);bridge.ack(f)
  if bridge.stats()['depth']==0 and ((f['config_word']>>8)&255)==HIGH and bool(f['config_word']&(1<<25))==(PASSES==4):break
 else:raise AssertionError('Failed to drain queue and apply parameters')
 return f
def run():
 t.action('pause')
 while t.state()['busy']:time.sleep(.05)
 t.action('disconnect');bridge=EthernetBridge('169.254.200.10');bridge.passes=PASSES;rows=[]
 try:
  empty(bridge);before=bridge.stats();assert before['version']==0x12000
  source={s['id']:s for s in json.loads((B/'data/real_tiles/manifest.json').read_text())['samples']}
  items=json.loads((R/'data/real_tiles/hdmi_manifest.json').read_text())['items']
  for item in items:
   if item['label'] not in ('crack','good'):continue
   n=item['index'];command=f'real_{n:03d}';t.action('display',value=command)
   end=time.monotonic()+5
   while True:
    if time.monotonic()>end:raise TimeoutError(command)
    try:player=json.loads((R/'host/player_status.json').read_text(encoding='utf-8-sig'))
    except (PermissionError,FileNotFoundError,json.JSONDecodeError):time.sleep(.025);continue
    if player['source']==command:break
    time.sleep(.03)
   time.sleep(.18)
   for _ in range(6):
    f,im,mask=bridge.capture(HIGH);bridge.ack(f)
    code=np.asarray(Image.open(io.BytesIO(im)).convert('RGB'))
    identity=sum(int(code[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))
    if identity==0x6000+n:break
   else:raise AssertionError('HDMI frame identity mismatch')
   assert bool(f['config_word']&(1<<25))==(PASSES==4) and f['config_word']&(1<<24) and ((f['config_word']>>8)&255)==HIGH
   image=Image.open(io.BytesIO(im));actual=np.asarray(Image.open(io.BytesIO(mask)))>0
   expected,_=detect(image,threshold=HIGH,passes=PASSES);rr=regions(expected);diff=int((actual!=expected).sum())
   gt=np.zeros((720,1280),bool);s=source[item['id']]
   if s.get('mask'):gt[110:610,390:890]=np.asarray(Image.open(B/'data/real_tiles'/s['mask']).convert('L').resize((500,500),Image.Resampling.NEAREST))>0
   row=dict(index=n,id=item['id'],label=item['label'],barcode=identity,frame=f,mismatch=diff,boxes_match=f['boxes']==rr['boxes'] and f['region_areas']==rr['areas'] and f['region_overflow']==rr['overflow'],tp=int((actual&gt).sum()),fp=int((actual&~gt).sum()),fn=int((~actual&gt).sum()))
   reference=R.parent/'pynq_z2_tile_v1_24/reports/v124/real_board'/f'{command}_original.png'
   assert reference.exists(),'Missing finalized V1.24 source image'
   baseline_rgb=np.asarray(Image.open(reference).convert('RGB'))
   row['baseline_rgb_mismatch']=int(np.count_nonzero(np.asarray(image.convert('RGB'))!=baseline_rgb))
   assert all(f[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   row['passed']=diff==0 and row['boxes_match'] and row['baseline_rgb_mismatch']==0;rows.append(row)
   (OUT/f'{command}_original.png').write_bytes(im);(OUT/f'{command}_mask.png').write_bytes(mask)
   (OUT/'progress.json').write_text(json.dumps(rows,indent=2))
   print(json.dumps(dict(index=n,label=item['label'],alarm=f['alarm'],pixels=f['candidate_pixels'],exact=row['passed'])),flush=True)
   assert row['passed'];empty(bridge)
  after=bridge.stats();crack=[r for r in rows if r['label']=='crack'];tp=sum(r['tp'] for r in crack);fp=sum(r['fp'] for r in crack);fn=sum(r['fn'] for r in crack)
  summary=dict(scope='Actual V1.32 HDMI/PL/TCP historical regression, not blind factory accuracy; profiles frozen before this run',samples=len(rows),pixel_exact=sum(r['passed'] for r in rows),before=before,after=after,high=HIGH,low=(HIGH+1)//2,support=3,passes=PASSES,counts={label:dict(total=sum(r['label']==label for r in rows),alarms=sum(r['label']==label and r['frame']['alarm'] for r in rows)) for label in ('crack','good')},pixel_recall=tp/(tp+fn),pixel_precision=tp/(tp+fp),items=rows)
  summary['passed']=len(rows)==50 and all(r['passed'] for r in rows) and all(after[k]==before[k] for k in ('gaps','invalid','dropped')) and summary['counts']['good']['alarms']==0 and summary['counts']['crack']['alarms']==17
  (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ('items','before','after')}),flush=True);assert summary['passed']
 finally:
  t.action('display',value='station_6');bridge.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--legacy',action='store_true');args=ap.parse_args()
 if args.legacy:HIGH=89;PASSES=2;OUT=R/'reports/v132/real_board_legacy'
 OUT.mkdir(parents=True,exist_ok=True);run()
