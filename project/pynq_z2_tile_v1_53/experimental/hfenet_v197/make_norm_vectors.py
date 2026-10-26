"""Synthetic arithmetic fixtures, not tile photographs or accuracy evidence."""
from pathlib import Path
import argparse,json,math,hashlib
import numpy as np
def even(n,d):
    sign=-1 if n<0 else 1;q,r=divmod(abs(n),d)
    return sign*(q+int(2*r>d or (2*r==d and q&1)))
def coefficients(n,s,q,eps,gamma,beta,exp):
    variance=n*q-s*s+eps;root=math.isqrt(variance);e=6-exp
    a=even(gamma*(1<<max(0,e)),root*(1<<max(0,-e))) if root else 0
    b=beta*(1<<e) if e>=0 else even(beta,1<<(-e))
    return [root,a&((1<<64)-1),b&((1<<64)-1),0,variance&((1<<64)-1),variance>>64],a,b
def packet(n,s,q,eps,gamma,beta,exp):return [n,s&((1<<64)-1),q,eps&((1<<64)-1),eps>>64,gamma&((1<<64)-1),beta&((1<<64)-1),exp&((1<<64)-1)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);rng=np.random.default_rng(197)
    groups=[rng.integers(-32768,32768,64,dtype='i2'),np.full(64,123,dtype='i2'),np.r_[np.full(63,200),201].astype('i2'),rng.integers(-20,21,64,dtype='i2')]
    settings=[(3,2**30,0,-10),(0,2**30,-3*2**29,-12),(0,-2**30,2**28,-14),(1<<80,2**29,-2**27,-8)]
    def build(suffix,data):
        pp=[];cc=[];oo=[]
        for values,(eps,gamma,beta,exp) in zip(data,settings):
            n=len(values);s=sum(int(x) for x in values);q=sum(int(x)**2 for x in values);pack=packet(n,s,q,eps,gamma,beta,exp)
            # Mode2 must recompute moments; deliberately poison these fields.
            pack[1]=0;pack[2]=0;pp+=pack
            expected,aa,bb=coefficients(n,s,q,eps,gamma,beta,exp);cc+=expected
            oo.extend(max(-32768,min(32767,even((n*int(x)-s)*aa+bb,1<<36))) for x in values)
        np.asarray(pp,dtype='<u8').tofile(a.out/('params'+suffix+'.bin'));np.asarray(cc,dtype='<u8').tofile(a.out/('coeff'+suffix+'.bin'))
        np.concatenate(data).astype('<i2').tofile(a.out/('pixels'+suffix+'.bin'));np.asarray(oo,dtype='<i2').tofile(a.out/('output'+suffix+'.bin'))
    build('',groups);build('2',[np.full(64,7,dtype='i2') for _ in range(4)])
    cases=[(360448,0,360448*32768**2,0,2**30,0,-10),(360448,360448*32767,360448*32767**2,0,2**30,-2**29,-12),(1,0,4,(1<<127)+1234567,3,5,6),(1,0,4,0,3,5,6),(1,0,4,0,5,-5,6),(1,0,4,0,-3,-7,6)]
    params=[];out=[]
    for case in cases:params+=packet(*case);out+=coefficients(*case)[0]
    np.asarray(params,dtype='<u8').tofile(a.out/'coefficient_params.bin');np.asarray(out,dtype='<u8').tofile(a.out/'coefficient_expected.bin')
    files=[dict(file=f.name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(a.out.glob('*.bin'))]
    (a.out/'proof.json').write_text(json.dumps(dict(scope='SYNTHETIC_INTEGER_ARITHMETIC_NOT_TILE_ACCURACY',channels=4,pixels_per_channel=64,coefficient_cases=len(cases),coverage=['PL moment computation despite poisoned supplied moments','second frame reset','constant input','nearconstant saturating output','negative affine','variance above64bits and root above signed64','nearest-even signed ties','invalid geometry/configuration rejected'],files=files),indent=2),encoding='utf8')
    print(json.dumps(dict(out=str(a.out),files=len(files))))
if __name__=='__main__':main()
