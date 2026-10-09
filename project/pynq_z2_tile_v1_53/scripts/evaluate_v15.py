"""Reproducible offline calibration and multi-source audit, NEVER a live detector."""
from pathlib import Path
import sys,json,hashlib,collections,concurrent.futures
import numpy as np
from PIL import Image,ImageDraw,ImageOps
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import detect,valley
from regions_reference import regions
OUT=R/'reports/v15/benchmark';OUT.mkdir(parents=True,exist_ok=True)
(OUT/'previews').mkdir(exist_ok=True)
def scene(path):
    photo=ImageOps.exif_transpose(Image.open(path)).convert('RGB');photo.thumbnail((500,500),Image.Resampling.BILINEAR)
    # Preserve aspect ratio and do not upscale low resolution photographs.
    im=Image.new('RGB',(1280,720),(30,39,44));im.paste(photo,((1280-photo.width)//2,(720-photo.height)//2));return im
mvroot=R/'data/real_tiles';mv=json.loads((mvroot/'manifest.json').read_text())
cal=[]
for s in mv['samples']:
    if s['split']!='train':continue
    im=scene(mvroot/s['image']);a=np.asarray(im,dtype=np.int32);g=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    score=valley(g)[80:640,80:1200];critical=int(np.partition(score.ravel(),-32)[-32]);cal.append(dict(id=s['id'],sha256=hashlib.sha256((mvroot/s['image']).read_bytes()).hexdigest(),critical_score=critical))
threshold=int(np.percentile([x['critical_score'] for x in cal],99,method='higher'))
calibration=dict(method='99th percentile higher of each training-normal frame 32nd highest opposed-valley score; no test labels used to set numeric threshold',selection_note='Architecture and percentile explored on historical MVTec regression; not a blind benchmark. Newly acquired sources are frozen cross-domain stress data, not tuning targets.',threshold=threshold,normal_training_count=len(cal),items=cal)
(OUT/'calibration.json').write_text(json.dumps(calibration,indent=2))
assert threshold<=255
recipes=[dict(id='synthetic_v14',name='合成演示与低纹理表面',threshold=36,description='保留 V1.4 参数；真实复杂纹理可能严重误报',scope='synthetic regression',calibration_sha256=None),dict(id='mvtec_tile_v15',name='MVTec 纹理瓷砖标定',threshold=threshold,description='230 张正常训练图标定；只适用于相近纹理、光照与成像尺度，存在漏检风险',scope='MVTec AD tile at 500 px, radius 8',calibration_sha256=hashlib.sha256((OUT/'calibration.json').read_bytes()).hexdigest())]
catalog_path=R/'host/recipes.json'
# Re-running the source-image benchmark must not erase separately measured
# HDMI/video profiles. They have their own normal-only calibration evidence.
if catalog_path.exists():
    prior=json.loads(catalog_path.read_text(encoding='utf-8'))['recipes']
    recipes += [r for r in prior if r['id'] not in ('synthetic_v14','mvtec_tile_v15')]
catalog_path.write_text(json.dumps(dict(version=1,default='synthetic_v14',recipes=recipes),ensure_ascii=False,indent=2),encoding='utf-8')
jobs=[]
for s in mv['samples']:
    if s['split']=='test':jobs.append(dict(dataset='mvtec',id=s['id'],split='historical_test',label=s['label'],source_image=str(mvroot/s['image']),mask=str(mvroot/s['mask']) if s.get('mask') else None,source=mv['primary_source'],license=mv['license']))
roof=R/'data/ceramics_mendeley'
if (roof/'download_result.json').exists():
    result=json.loads((roof/'download_result.json').read_text());assert result['verified']==1600
    for s in json.loads((roof/'manifest.json').read_text())['samples']:
        jobs.append(dict(dataset='roof_ceramic',id=s['id'],split='cross_domain_'+s['split'],label=s['label'],source_image=str(roof/s['image']),source='https://data.mendeley.com/datasets/47x6jdbr5j/1',license='CC BY 4.0'))
author=R/'data/ceramic_cracks_author/ceramic-cracks-dataset-master'
for split,folder in [('development_labeled',author/'train/image'),('unlabeled_public',author/'test')]:
    for p in sorted(folder.glob('*.png')):
        mask=author/'train/label'/p.name if split=='development_labeled' else None
        jobs.append(dict(dataset='facade_ceramic',id=split+'/'+p.stem,split=split,label='crack_collection_no_image_negative_labels',source_image=str(p),mask=str(mask) if mask else None,source='https://github.com/gerivansantos/ceramic-cracks-dataset',license='No explicit repository license found; local research only, excluded from redistribution'))
def evaluate(pair):
    i,s=pair;im=scene(s['source_image']);s=dict(s,index=i,image=f'previews/{i:04d}.jpg',sha256=hashlib.sha256(Path(s['source_image']).read_bytes()).hexdigest())
    s['predictions']={}
    for name,t in [('baseline',36),('calibrated',threshold)]:
        mask,_=detect(im,threshold=t);rr=regions(mask);s['predictions'][name]=dict(threshold=t,alarm=bool(rr['boxes'] or rr['overflow']),candidate_pixels=int(mask.sum()),**rr)
        if s.get('mask'):
            original=ImageOps.exif_transpose(Image.open(s['source_image']));size=original.size;scale=min(1,500/size[0],500/size[1]);size=(round(size[0]*scale),round(size[1]*scale))
            gt=np.zeros((720,1280),bool);m=np.asarray(Image.open(s['mask']).convert('L').resize(size,Image.Resampling.NEAREST))>0
            top=(720-size[1])//2;left=(1280-size[0])//2;gt[top:top+size[1],left:left+size[0]]=m
            tp=int((mask&gt).sum());fp=int((mask&~gt).sum());fn=int((~mask&gt).sum())
            s['predictions'][name]['pixel']=dict(tp=tp,fp=fp,fn=fn,iou=tp/(tp+fp+fn) if tp+fp+fn else None)
    im.resize((960,540)).save(OUT/s['image'],quality=87)
    return s
rows=[]
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    for row in pool.map(evaluate,enumerate(jobs)):
        rows.append(row)
        if len(rows)%100==0:print('evaluated',len(rows),'/',len(jobs),flush=True)
summary={}
for dataset in sorted(set(s['dataset'] for s in rows)):
    group=[s for s in rows if s['dataset']==dataset];metrics={}
    for mode in ('baseline','calibrated'):
        counts={label:dict(n=sum(s['label']==label for s in group),alarms=sum(s['label']==label and s['predictions'][mode]['alarm'] for s in group)) for label in sorted(set(s['label'] for s in group))}
        p=[s['predictions'][mode]['pixel'] for s in group if 'pixel' in s['predictions'][mode]];sums={k:sum(s[k] for s in p) for k in ('tp','fp','fn')}
        metrics[mode]=dict(counts=counts,pixel_micro_iou=sums['tp']/sum(sums.values()) if sum(sums.values()) else None,pixel_labeled_count=len(p))
    summary[dataset]=dict(images=len(group),unique_sha256=len(set(s['sha256'] for s in group)),metrics=metrics)
result=dict(scope='OFFLINE FIXED-POINT REFERENCE, NOT BOARD RESULTS; no factory accuracy claim',threshold=threshold,calibration_images=len(cal),evaluated_images=len(rows),summary=summary,items=rows)
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False),flush=True)
