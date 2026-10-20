"""Fixed arithmetic vectors, source-bound; no image accuracy claim."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
import reference_v166 as metric
from reference_tile import sha

def pack(fields):
    value=0
    for number,width in fields:value=(value<<width)|(int(number)&((1<<width)-1))
    return value

def oracle(ref,cur,span,edge,high,low):
    rf=metric.features(ref)[1,1].astype(int);cf=metric.features(cur)[1,1].astype(int)
    def chroma(a):
        r,g,b=map(int,a[1,1]);return np.array([(r-b+256)>>1,(-r+2*g-b+512)>>2])
    score=int(max(np.abs(rf-cf).max(),np.maximum(np.abs(chroma(ref)-chroma(cur))-span,0).max()))
    return score,score>high+edge,score>low+(edge>>1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(16620261020);inputs=[];outputs=[]
    for i in range(8192):
        ref=rng.integers(0,256,(3,3,3),dtype=np.uint8);cur=rng.integers(0,256,(3,3,3),dtype=np.uint8);span=rng.integers(0,256,2);edge,high,low=map(int,rng.integers(0,256,3))
        if i<256:ref[:]=i;cur[:]=i;span[:]=0;edge=high=low=0
        elif i<512:
            ref[:]=128;cur[:]=128;cur[1,1]=[min(255,i-256+40),i-256,max(0,i-256-40)];span[:]=0;edge=0;high=18;low=9
        score,strong,weak=oracle(ref,cur,span,edge,high,low)
        if 512<=i<768:edge=0;high=score;low=score
        score,strong,weak=oracle(ref,cur,span,edge,high,low);sof=int(i%97==0);eol=int(i%127==126)
        fields=[*[(v,8) for v in cur.ravel()],*[(v,8) for v in ref.ravel()],(span[0],8),(span[1],8),(edge,8),(high,8),(low,8),(i,32),(sof,1),(eol,1)]
        inputs.append(pack(fields));outputs.append(pack([(score,8),(strong,1),(weak,1),(i,32),(sof,1),(eol,1)]))
    for name,values,width in [('input.mem',inputs,127),('expected.mem',outputs,11),('board_input.mem',inputs[:2048],127),('board_expected.mem',outputs[:2048],11)]:
        (a.out/name).write_text(''.join(f'{v:0{width}x}\n' for v in values))
    proof=dict(vectors=8192,board_vectors=2048,implementation=metric.implementation(),generator_sha256=sha(__file__),rtl_sha256=sha(ROOT/'experimental/reference_v166/rtl/reference_metric_v166.v'),testbench_sha256=sha(ROOT/'sim/tb_reference_metric_v166.sv'),sha256={p.name:sha(p) for p in a.out.iterdir()})
    (a.out/'manifest.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))

if __name__=='__main__':main()
