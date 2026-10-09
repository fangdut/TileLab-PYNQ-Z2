"""Independent NumPy scores for changing images, wide cracks and frame borders."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
O=R/'reports/v152/dual_scale_vectors';O.mkdir(parents=True,exist_ok=False)
W,H,F=80,64,4;rng=np.random.default_rng(152);y,x=np.indices((H,W))
images=[rng.integers(0,256,(H,W)),np.full((H,W),180),np.full((H,W),205),((x*7+y*3)%256)]
images[1][:,31:52]=100;images[1][20:40,39:44]=20
images[2][5:60,9:12]=25;images[2][10:15,4:77]=80;images[2][54:61,4:77]=60
responses={n:[valley(a,n) for a in images] for n in (8,16)}
for name,arrays in [('gray',images),('score8',responses[8]),('score16',responses[16])]:
    (O/(name+'.mem')).write_text('\n'.join(f'{int(v):02x}' for a in arrays for v in a.ravel())+'\n',encoding='ascii')
assert any(np.any(a!=b) for a,b in zip(responses[8],responses[16]))
proof=dict(frames=F,width=W,height=H,pixels=F*W*H,seed=152,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('*.mem')},
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),R/'models/valley_reference.py')})
(O/'metadata.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof))
