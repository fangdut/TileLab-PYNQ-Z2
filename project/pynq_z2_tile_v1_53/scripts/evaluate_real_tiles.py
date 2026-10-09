"""Fixed pre-existing threshold, official test split; no test-set tuning.
Images are real MVTec photos. HDMI scenes and motion are explicitly composites.
"""
from pathlib import Path
import sys,json,collections,hashlib
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import detect
from regions_reference import regions
D=R/'data/real_tiles';OUT=R/'reports/v14/real_dataset';OUT.mkdir(parents=True,exist_ok=True)
HDMI=D/'hdmi';HDMI.mkdir(exist_ok=True)
manifest=json.loads((D/'manifest.json').read_text());samples=[s for s in manifest['samples'] if s['split']=='test']
rows=[];totals=np.zeros(3,dtype=np.int64)
for n,s in enumerate(samples):
    photo=Image.open(D/s['image']).convert('RGB');assert photo.size==(840,840)
    im=Image.new('RGB',(1280,720),(30,39,44));im.paste(photo.resize((500,500),Image.Resampling.BILINEAR),(390,110))
    draw=ImageDraw.Draw(im);draw.text((24,23),f"MVTec AD tile | REAL PHOTO / COMPOSITE HDMI SCENE | {n:03d} {s['id']}",fill=(200,215,220))
    draw.text((24,680),'Source: MVTec Software GmbH | CC BY-NC-SA 4.0 | Test set; fixed threshold 36',fill=(190,210,215))
    im.save(HDMI/f'real_{n:03d}.png')
    pred,_=detect(im,threshold=36);rr=regions(pred);alarm=bool(rr['boxes'] or rr['overflow'])
    gt=np.zeros((720,1280),dtype=bool)
    if s.get('mask'):gt[110:610,390:890]=np.asarray(Image.open(D/s['mask']).convert('L').resize((500,500),Image.Resampling.NEAREST))>0
    tp=int(np.count_nonzero(pred&gt));fp=int(np.count_nonzero(pred&~gt));fn=int(np.count_nonzero(~pred&gt))
    totals+=np.array([tp,fp,fn]);iou=tp/(tp+fp+fn) if tp+fp+fn else None
    row=dict(index=n,id=s['id'],label=s['label'],image=f'hdmi/real_{n:03d}.png',alarm=alarm,candidate_pixels=int(pred.sum()),boxes=rr['boxes'],region_overflow=rr['overflow'],pixel_tp=tp,pixel_fp=fp,pixel_fn=fn,iou=iou)
    rows.append(row)
    if n%20==0:print(f'Evaluated {n+1}/{len(samples)}',flush=True)
counts=collections.Counter(s['label'] for s in samples)
conf={k:sum(s['label']=='crack' and s['alarm']==v for s in rows) for k,v in [('tp',True),('fn',False)]}
conf.update({k:sum(s['label']=='good' and s['alarm']==v for s in rows) for k,v in [('fp',True),('tn',False)]})
conf.update(recall=conf['tp']/17,false_positive_rate=conf['fp']/33,precision=conf['tp']/(conf['tp']+conf['fp']) if conf['tp']+conf['fp'] else 0)
result=dict(scope='OFFLINE REFERENCE ONLY; real photographed tiles on composite HDMI background, not physical conveyor accuracy',threshold=36,radius=8,roi=[80,80,1199,639],resize='840x840 to 500x500 bilinear; GT nearest',split='Official test; parameters frozen before reading images',counts=counts,crack_vs_good=conf,other_defect_alarm_counts={label:sum(s['label']==label and s['alarm'] for s in rows) for label in counts if label not in ('good','crack')},pixel_metrics=dict(tp=int(totals[0]),fp=int(totals[1]),fn=int(totals[2]),micro_iou=float(totals[0]/sum(totals))),items=rows)
(OUT/'metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(D/'hdmi_manifest.json').write_text(json.dumps(dict(provenance='REAL_MVTEC_PHOTO_COMPOSITE',license=manifest['license'],source=manifest['primary_source'],items=rows),indent=2),encoding='utf-8')
# Examples are selected by fixed dataset order, not favorable detection outcomes.
examples=[next(r for r in rows if r['label']==label) for label in ('good','crack','glue_strip','rough')]
sheet=Image.new('RGB',(1280,840),'white');d=ImageDraw.Draw(sheet)
for k,row in enumerate(examples):
    im=Image.open(D/row['image']);ov=ImageDraw.Draw(im)
    for b in row['boxes']:ov.rectangle(b,outline='red',width=3)
    x=(k%2)*640;y=(k//2)*420;sheet.paste(im.resize((640,360)),(x,y));d.text((x+12,y+370),f"{row['label']} | alarm={row['alarm']} | candidates={row['candidate_pixels']} | OFFLINE",fill='black')
sheet.save(OUT/'examples.png')
print(json.dumps(dict(crack_vs_good=conf,counts=counts)),flush=True)
