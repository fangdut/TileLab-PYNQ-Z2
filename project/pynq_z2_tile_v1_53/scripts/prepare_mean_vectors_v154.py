"""Regenerate standalone score vectors in a new directory, offline only."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from directional_mean_reference import directional_mean_score
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=R/'reports/v154/mean_vectors');args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    W,H,F=80,64,4;rng=np.random.default_rng(154);y,x=np.indices((H,W))
    frames=[rng.integers(0,256,(H,W)),np.full((H,W),180),np.full((H,W),205),((x*7+y*3)%256)]
    frames[1][:,31:52]=100;frames[1][20:40,39:44]=20
    frames[2][5:60,9:12]=25;frames[2][10:15,4:77]=80;frames[2][54:61,4:77]=60
    cases={'gray':frames,'score8':[valley(a,8) for a in frames],'score16':[valley(a,16) for a in frames],
           'short':[directional_mean_score(a,8) for a in frames],'long':[directional_mean_score(a,16) for a in frames]}
    for name,arrays in cases.items():
        (args.out/(name+'.mem')).write_text('\n'.join(f'{int(v):02x}' for a in arrays for v in a.ravel())+'\n',encoding='ascii')
    proof=dict(seed=154,width=W,height=H,frames=F,pixels=F*W*H,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.glob('*.mem')})
    (args.out/'metadata.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof))
if __name__=='__main__':main()
