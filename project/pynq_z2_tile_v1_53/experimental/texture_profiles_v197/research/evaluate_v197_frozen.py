"""Freeze expanded L1 candidate before opening another file-level pilot."""
from pathlib import Path
import io,json,zipfile,hashlib,sys,datetime
import numpy as np
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');O=W/'v197_new80_01';O.mkdir(exist_ok=False)
sys.path.insert(0,str(P/'experimental/texture_profiles_v197'));from reference import sample_rgb,extract,decide
sha=lambda b:hashlib.sha256(b).hexdigest()
frozen=json.loads((W/'v197_expanded01/frozen.json').read_text());model=next(m for m in frozen['models'] if m['name']=='l1')
assert min(model['cal_counts'].values())>=8
freeze=dict(scope='INTEGER_NORMAL_DESCRIPTOR_L1_GROUPING_LINE_PILOT_NOT_TRUE_FLOWER_IDS',selection='Chosen on exposed80 only; previous weighted detection34/40 FP4/40; expanded L1 development38/40 FP3/40',mode='weighted',model=model,source_sha256=sha((P/'experimental/texture_profiles_v197/reference.py').read_bytes()),normal_manifest_sha256=sha((W/'v197_expanded01/normal_manifest.json').read_bytes()),frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),test_started=False)
(O/'frozen_model.json').write_text(json.dumps(freeze,indent=2),encoding='utf8')
old=json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images']+json.loads((W/'v196_hfe_holdout01/manifest.json').read_text())['images']+json.loads((W/'v197_expanded01/normal_manifest.json').read_text())
used={r['original_rgb_sha256'] for r in old};used_crops=set()
for r in old:
    base=Path(r['base']) if 'base' in r else W/('v196_dataset_hfe01' if any(q['id']==r['id'] for q in json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images']) else 'v196_hfe_holdout01')
    used_crops.add(sha(np.asarray(Image.open(base/r['file']).convert('RGB')).tobytes()))
z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');paths=sorted([p for p in z.namelist() if '/valid/img/' in p and p.endswith('.bmp')],key=lambda p:sha(('v197-new-files|'+p).encode()))
for sub in ['prepared','masks']:(O/sub).mkdir()
selected=[];counts=dict(good=0,defect=0)
for path in paths:
    raw=z.read(path);rgb=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'));rs=sha(rgb.tobytes())
    if rs in used:continue
    assert rgb.shape==(1408,256,3);y=704*(int(sha(('v196-hfe-view|'+path).encode())[:8],16)%2);crop=rgb[y:y+704];cs=sha(crop.tobytes())
    if cs in used_crops:continue
    mask_path=path.replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';mraw=z.read(mask_path);mask=np.asarray(Image.open(io.BytesIO(mraw)).convert('L'))[y:y+704]>1
    label='defect' if mask.any() else 'good'
    if counts[label]>=40:continue
    ident=sha(('HFENet|'+path).encode())[:24];file=O/'prepared'/(ident+'.png');gt=O/'masks'/(ident+'.png');Image.fromarray(crop).save(file);Image.fromarray((mask*255).astype('u1')).save(gt)
    selected.append(dict(id=ident,archive_path=path,original_sha256=sha(raw),original_rgb_sha256=rs,original_mask_sha256=sha(mraw),crop_rgb_sha256=cs,crop=[0,y,256,704],file='prepared/'+file.name,mask='masks/'+gt.name,prepared_sha256=sha(file.read_bytes()),mask_sha256=sha(gt.read_bytes()),label=label))
    counts[label]+=1;used.add(rs);used_crops.add(cs)
    if counts==dict(good=40,defect=40):break
assert len(selected)==80
plan=dict(scope='FROZEN_NEW_FILE_PILOT_NOT_PHYSICAL_TILE_INDEPENDENT',freeze_sha256=sha((O/'frozen_model.json').read_bytes()),counts=counts,source='https://github.com/RobotvisionLab/HFENet',selection='SHA order v197-new-files; one fixed704row half per source by unchanged v196 policy; exact pixels; RGB/crop hashes exclude all prior roles',physical_specimen_independence=False,model_changed_after_test=False)
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8');(O/'manifest.json').write_text(json.dumps(dict(images=selected,plan_sha256=sha((O/'plan.json').read_bytes())),indent=2),encoding='utf8')
results=[]
for row in selected:
    stats=extract(sample_rgb(Image.open(O/row['file']).convert('RGB')));decision=decide(stats,model)
    gt=np.asarray(Image.open(O/row['mask']).convert('L'))>1;flags=decision['flags'].any(1)
    results.append(dict(id=row['id'],label=row['label'],alarm=decision['alarm'],group=decision['group'],strict_gt_column_hit=bool((flags&gt.any(0)).any()),vote_columns=np.flatnonzero(flags).tolist()))
tp=sum(r['label']=='defect' and r['alarm'] for r in results);fp=sum(r['label']=='good' and r['alarm'] for r in results)
summary=dict(scope='FROZEN_NEW80_NUMPY_OFFLINE_NOT_BOARD',cases=80,tp=tp,fp=fp,tn=40-fp,fn=40-tp,defect_recall=tp/40,normal_false_positive_rate=fp/40,strict_gt_column_hits=sum(r['label']=='defect' and r['strict_gt_column_hit'] for r in results),physical_specimen_independence=False,board_verified=False,integrated_with_station=False)
(O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))
