from pathlib import Path
from PIL import Image
import zipfile,io,json,numpy as np
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');names=set(z.namelist())
common=sorted(p for p in names if '/no_defective/img/' in p and p.lower().endswith('.bmp') and p.replace('/no_defective/','/defective/') in names)
rows=[]
for p in common[:20]:
    other=p.replace('/no_defective/','/defective/');a=np.asarray(Image.open(io.BytesIO(z.read(p))).convert('RGB'));b=np.asarray(Image.open(io.BytesIO(z.read(other))).convert('RGB'))
    gt=other.replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';mask=np.asarray(Image.open(io.BytesIO(z.read(gt))).convert('L'))>1
    if a.shape!=b.shape:rows.append(dict(file=p,shape_matches=False));continue
    same=np.all(a==b,axis=2)
    rows.append(dict(file=p,shape_matches=True,pixel_equal_fraction=float(same.mean()),
        outside_label_equal_fraction=float(same[~mask].mean()),changed_pixels=int((~same).sum()),label_pixels=int(mask.sum())))
out=dict(common_names=len(common),checked=rows,
    interpretation='Same stem does not establish same physical source; high pixel agreement outside defect annotations would require explicit provenance review, not a claim of authentic physical damage')
(W/'v196_hfenet01/paired_name_audit.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
