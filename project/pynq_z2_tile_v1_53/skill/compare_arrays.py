from pathlib import Path
import argparse,hashlib,json
import numpy as np
def compare(expected,actual):
    a=np.load(expected,allow_pickle=False);b=np.load(actual,allow_pickle=False)
    if not isinstance(a,np.ndarray) or not isinstance(b,np.ndarray) or a.dtype!=b.dtype or a.shape!=b.shape:raise ValueError('Array shape/dtype mismatch; no implicit conversion')
    different=np.flatnonzero((a!=b).ravel());first=tuple(int(i) for i in np.unravel_index(int(different[0]),a.shape)) if different.size else None
    return dict(equal=not bool(different.size),elements=int(a.size),mismatches=int(different.size),first_mismatch=first,shape=list(a.shape),dtype=str(a.dtype),expected_sha256=hashlib.sha256(Path(expected).read_bytes()).hexdigest(),actual_sha256=hashlib.sha256(Path(actual).read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser();p.add_argument('--expected',required=True,type=Path);p.add_argument('--actual',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();result=compare(a.expected,a.actual)
    with a.out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result));raise SystemExit(0 if result['equal'] else 1)
if __name__=='__main__':main()
