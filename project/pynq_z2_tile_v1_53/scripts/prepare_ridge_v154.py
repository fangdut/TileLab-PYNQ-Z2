"""Create independent integer golden vectors; never overwrite old evidence."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from coherent_ridge_candidate import coherent_ridge_score
out=R/'reports/v154/ridge_vectors'
out.mkdir(parents=True,exist_ok=False)
W,H,F=80,64,4;rng=np.random.default_rng(154);y,x=np.indices((H,W))
images=[rng.integers(0,256,(H,W)),np.full((H,W),180),np.full((H,W),205),((x*7+y*3)%256)]
images[1][:,31:52]=100;images[1][20:40,39:44]=20
images[2][5:60,9:12]=25;images[2][10:15,4:77]=80;images[2][54:61,4:77]=60
for name,arrays in [('gray',images),('score8',[valley(a,8) for a in images]),
                    ('score16',[valley(a,16) for a in images]),('ridge',[coherent_ridge_score(a) for a in images])]:
    (out/(name+'.mem')).write_text('\n'.join(f'{int(v):02x}' for a in arrays for v in a.ravel())+'\n',encoding='ascii')
assert any(np.any(coherent_ridge_score(a)>24) for a in images)
proof=dict(seed=154,width=W,height=H,frames=F,pixels=F*W*H,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.mem')})
(out/'metadata.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps(proof))
