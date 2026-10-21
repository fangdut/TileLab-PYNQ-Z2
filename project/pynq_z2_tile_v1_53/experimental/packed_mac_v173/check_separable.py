"""Independent exact-integer interpolation identity/range check, offline only."""
from pathlib import Path
import argparse,hashlib,json,random


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    rng=random.Random(17331);tested=0;max_row=0;max_value=0
    shapes=[(1,1),(1,1024),(1024,1),(79,65),(720,720),(840,840),(1024,1024),(27,29)]
    shapes += [(rng.randrange(1,1025),rng.randrange(1,1025)) for _ in range(80)]
    for w,h in shapes:
        for grid in [1,4,10,28]:
            xd,yd=2*w,2*h
            for sample in range(500):
                x=rng.randrange(w);y=rng.randrange(h)
                xx=max(0,min((2*x+1)*grid-w,(grid-1)*xd))
                yy=max(0,min((2*y+1)*grid-h,(grid-1)*yd))
                fx,fy=xx%xd,yy%yd;dx,dy=xd-fx,yd-fy
                a,b,c,d=[rng.randrange(1<<20) for _ in range(4)]
                if sample%10==0:a,b,c,d=[(1<<20)-1]*4
                original=(a*dx+b*fx)*dy+(c*dx+d*fx)*fy
                left=a*dy+c*fy;right=b*dy+d*fy
                separated=left*dx+right*fx
                if original!=separated or max(left,right)>=(1<<32) or separated>=(1<<44):
                    raise ValueError('Exact numerator or range mismatch')
                max_row=max(max_row,left,right);max_value=max(max_value,separated);tested+=1
    source=Path(__file__).with_name('texture_packed_separable.cpp')
    report=dict(scope='OFFLINE_INTEGER_REARRANGEMENT_AND_RANGE_CHECK_NOT_RTL_OR_BOARD',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),seed=17331,
        grid_values=[1,4,10,28],samples=tested,all_numerators_exact=True,
        max_vertical_observed=max_row,max_numerator_observed=max_value,
        algebra='(a*dx+b*fx)*dy+(c*dx+d*fx)*fy == (a*dy+c*fy)*dx+(b*dy+d*fy)*fx',
        universal_range_bound='vertical <= (2^20-1)*2048 < 2^32; numerator <= (2^20-1)*2048^2 < 2^44')
    text=json.dumps(report,indent=2)+'\n'
    if args.out:args.out.write_text(text)
    print(text,end='')


if __name__=='__main__':main()
