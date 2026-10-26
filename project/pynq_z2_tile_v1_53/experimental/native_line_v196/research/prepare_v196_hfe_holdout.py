from pathlib import Path
from PIL import Image
import zipfile,json,hashlib,io,datetime
import numpy as np
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');old=W/'v196_dataset_hfe01';O=W/'v196_hfe_holdout01';O.mkdir(exist_ok=False)
z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');sha=lambda b:hashlib.sha256(b).hexdigest()
prior=json.loads((old/'manifest.json').read_text())['images'];used={r['original_rgb_sha256'] for r in prior};used_crops={sha(np.asarray(Image.open(old/r['file']).convert('RGB')).tobytes()) for r in prior}
valid=sorted([p for p in z.namelist() if '/valid/img/' in p and p.endswith('.bmp')],key=lambda p:sha(('v196-native-new-eval|'+p).encode()))
selected=[];counts=dict(good=0,defect=0);cache={}
for path in valid:
    raw=z.read(path);im=Image.open(io.BytesIO(raw)).convert('RGB');full_rgb=sha(np.asarray(im).tobytes())
    if full_rgb in used:continue
    half=int(sha(('v196-hfe-view|'+path).encode())[:8],16)%2;y=704*half;crop=im.crop((0,y,256,y+704));crop_rgb=sha(np.asarray(crop).tobytes())
    if crop_rgb in used_crops:continue
    mpath=path.replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';mraw=z.read(mpath);mask=np.asarray(Image.open(io.BytesIO(mraw)).convert('L'))[y:y+704]>1
    label='defect' if mask.any() else 'good'
    if counts[label]>=20:continue
    ident=sha(('HFENet|'+path).encode())[:24];row=dict(id=ident,role='test',label=label,archive_path=path,mask_archive_path=mpath,
        original_sha256=sha(raw),original_rgb_sha256=full_rgb,crop_rgb_sha256=crop_rgb,original_mask_sha256=sha(mraw),crop=[0,y,256,704],defect_pixels=int(mask.sum()))
    selected.append(row);counts[label]+=1;used.add(full_rgb);used_crops.add(crop_rgb);cache[ident]=(raw,mraw,crop,mask)
    if counts==dict(good=20,defect=20):break
assert len(selected)==40
cal=json.loads((W/'v196_line_coherence01/frozen_calibration.json').read_text())
plan=dict(scope='UNSEEN_FILE_NATIVE_LINE_EVALUATION_NOT_INDEPENDENT_PHYSICAL_TILES',
    frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),algorithm='energy_weighted signed horizontal curvature across224 native-width sampled rows',
    spans=[2,4,8],thresholds=cal['thresholds']['energy_weighted'],
    decision='N*N >= (T+1)*(E+1) per column/scale, OR over valid columns and3 scales; exact floor(N*N/(E+1)) > T',
    source_sha256=sha((P/'experimental/native_line_v196/native_line.cpp').read_bytes()),
    chosen_using_previous40=True,new40_not_used_for_selection=True,old232_full_rgb_and_crop_rgb_disjoint=True,
    physical_piece_independence=False,source='https://github.com/RobotvisionLab/HFENet',
    crop_policy='Same original path SHA fixes one704-row half before defect scores, no rescale, one view per parent',
    selected_before_evaluation=selected,source_images_redistribution_not_assumed=True,
    limitations=['Printing-defect line-scan views, not complete tiles or arbitrary-direction cracks','Old40 used for algorithm choice; only this new file group assesses frozen choice','Physical original-tile groups absent'])
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
for name in ['originals','prepared','masks']:(O/name).mkdir()
manifest=[]
for row in selected:
    ident=row['id'];raw,mraw,im,mask=cache[ident];(O/'originals'/(ident+'.bmp')).write_bytes(raw);(O/'originals'/(ident+'_label.bmp')).write_bytes(mraw)
    file=O/'prepared'/(ident+'.png');im.save(file);maskfile=O/'masks'/(ident+'.png');Image.fromarray((mask*255).astype('uint8')).save(maskfile)
    manifest.append(dict(row,file='prepared/'+file.name,mask='masks/'+maskfile.name,prepared_sha256=sha(file.read_bytes()),mask_sha256=sha(maskfile.read_bytes())))
(O/'manifest.json').write_text(json.dumps(dict(images=manifest,plan_sha256=sha((O/'plan.json').read_bytes())),indent=2),encoding='utf8')
print(json.dumps(dict(images=len(manifest),counts=counts,plan_sha256=sha((O/'plan.json').read_bytes()))))
