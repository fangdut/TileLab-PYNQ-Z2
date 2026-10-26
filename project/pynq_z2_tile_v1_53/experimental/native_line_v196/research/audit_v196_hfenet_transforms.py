from pathlib import Path
from PIL import Image
import zipfile,io,numpy as np,json
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');names=set(z.namelist());root='HFENet_Dataset/valid/img/'
paths=sorted(p for p in names if p.startswith(root+'0') and p.endswith('.bmp'))[:16];out=[]
for p in paths:
    stem=Path(p).stem[1:];a=np.asarray(Image.open(io.BytesIO(z.read(p))).convert('RGB'));group=[]
    for prefix in ['1','2','3']:
        other=root+prefix+stem+'.bmp'
        if other not in names:continue
        b=np.asarray(Image.open(io.BytesIO(z.read(other))).convert('RGB'))
        if b.shape==a.shape:
            matches=[name for name,view in [('same',a),('flip_x',a[:,::-1]),('flip_y',a[::-1]),('flip_xy',a[::-1,::-1])] if np.array_equal(b,view)]
            group.append(dict(file=other,matches=matches))
    out.append(dict(base=p,variants=group))
result=dict(scope='EXACT_PIXEL_TRANSFORM_PROVENANCE_AUDIT',checks=out)
(W/'v196_hfenet01/transform_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
