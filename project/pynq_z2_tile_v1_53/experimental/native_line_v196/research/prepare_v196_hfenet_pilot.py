from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import zipfile,hashlib,json,io,datetime
import numpy as np
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');O=W/'v196_dataset_hfe01';O.mkdir(exist_ok=False)
source=W/'v196_hfenet01';z=zipfile.ZipFile(source/'HFENet_Dataset.zip')
sha=lambda b:hashlib.sha256(b).hexdigest()
train=[p for p in z.namelist() if '/train/no_defective/img/' in p and p.lower().endswith('.bmp')]
valid=[p for p in z.namelist() if '/valid/img/' in p and p.lower().endswith('.bmp')]
train.sort(key=lambda p:sha(('v196-hfe-normal|'+p).encode()));valid.sort(key=lambda p:sha(('v196-hfe-eval|'+p).encode()))
selected=[];seen=set()
def examine(path):
    raw=z.read(path);im=Image.open(io.BytesIO(raw)).convert('RGB')
    if im.size!=(256,1408):raise ValueError('Unexpected source geometry')
    pixels=np.asarray(im);pixel_sha=sha(pixels.tobytes())
    mask_path=path.replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';mask_raw=z.read(mask_path)
    mask=np.asarray(Image.open(io.BytesIO(mask_raw)).convert('L'))>1
    half=int(sha(('v196-hfe-view|'+path).encode())[:8],16)%2;y=704*half
    return dict(id=sha(('HFENet|'+path).encode())[:24],archive_path=path,mask_archive_path=mask_path,
        original_sha256=sha(raw),original_rgb_sha256=pixel_sha,original_mask_sha256=sha(mask_raw),
        crop=[0,y,256,704],label='defect' if bool(mask[y:y+704].any()) else 'good',defect_pixels=int(mask[y:y+704].sum()),
        full_image_defect_pixels=int(mask.sum())),raw,mask_raw,im,mask
cache={}
for path in train:
    row,raw,mraw,im,mask=examine(path)
    assert row['full_image_defect_pixels']==0,'Author normal directory has annotated defect'
    if row['original_rgb_sha256'] in seen:continue
    seen.add(row['original_rgb_sha256']);row['role']='memory' if len(selected)<128 else 'calibration'
    selected.append(row);cache[row['id']]=(raw,mraw,im,mask)
    if len(selected)==192:break
assert len(selected)==192
counts=dict(good=0,defect=0)
for path in valid:
    row,raw,mraw,im,mask=examine(path)
    if row['original_rgb_sha256'] in seen or counts[row['label']]>=20:continue
    seen.add(row['original_rgb_sha256']);row['role']='test';counts[row['label']]+=1
    selected.append(row);cache[row['id']]=(raw,mraw,im,mask)
    if counts==dict(good=20,defect=20):break
assert len(selected)==232
plan=dict(scope='HFENET_REAL_PATTERNED_FLOOR_TILE_LINE_SCAN_CROP_PILOT_NOT_WHOLE_TILE_ACCEPTANCE',
    frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),memory_normals=128,calibration_normals=64,test_normal=20,test_defect=20,
    source_repo='https://github.com/RobotvisionLab/HFENet',source_archive=json.loads((source/'source.json').read_text()),
    data_license='Author public research data; repository software MIT; separate data redistribution rights not assumed',
    crop_policy='One256x704 half per256x1408 original, half fixed by path SHA before labels or model scores. Exact pixel crop; no resize or defect synthesis.',
    center_rule='1024 deterministic farthest-first centers from128 normal memories, fixed CNN/projection',
    threshold_rule='maximum64 separate normal calibration scores plus1, freeze before test scores',
    evaluation_note='Author industrial patterned-tile line scans, printing-defect labels; exact cropped views, not whole physical tiles or independent-specimen validation',
    selected_before_model_fit=selected,split='author training normal folders for fit/cal; author validation for evaluation; no shared original RGB SHA',
    physical_piece_disjointness_established=False,cpu_gpu_runtime_detection=False,
    limitations=['One parent view per file; no independent physical tile identities supplied','Repository may contain preprocessing or related views; no native camera provenance beyond author statement','Printing surface defects must not all be called cracks','No automatic full-strip scanning deployed; this is a frozen-input offline preparation pilot'])
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
for name in ['originals','prepared','masks']:(O/name).mkdir()
manifest=[]
for row in selected:
    raw,mraw,im,mask=cache[row['id']];ident=row['id'];x,y,w,h=row['crop']
    (O/'originals'/(ident+'.bmp')).write_bytes(raw);(O/'originals'/(ident+'_label.bmp')).write_bytes(mraw)
    target=O/'prepared'/(ident+'.png');im.crop((x,y,x+w,y+h)).save(target)
    gt=O/'masks'/(ident+'.png');Image.fromarray((mask[y:y+h,x:x+w]*255).astype('uint8')).save(gt)
    manifest.append(dict(row,file='prepared/'+ident+'.png',mask='masks/'+ident+'.png',prepared_sha256=sha(target.read_bytes()),mask_sha256=sha(gt.read_bytes())))
(O/'manifest.json').write_text(json.dumps(dict(images=manifest,plan_sha256=sha((O/'plan.json').read_bytes())),indent=2),encoding='utf8')
# Review only; do not distribute source images under the software license.
test=[r for r in manifest if r['role']=='test'];sheet=Image.new('RGB',(1000,8*260),'white');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
for i,row in enumerate(test):
    im=Image.open(O/row['file']);im.thumbnail((190,224));x=i%5*200;y=i//5*260;sheet.paste(im,(x,y));draw.text((x,y+225),f"{row['label']} {row['defect_pixels']}px",fill='black',font=font);draw.text((x,y+242),row['id'][:16],fill='black',font=font)
sheet.save(O/'review_contactsheet.jpg')
print(json.dumps(dict(images=len(manifest),test=counts,source_geometry=[256,1408],prepared_geometry=[256,704],role_rgb_hashes_disjoint=True)))
