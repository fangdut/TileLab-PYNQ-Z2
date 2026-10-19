"""Fixed randomized arithmetic/handshake vectors; no images, model or training."""
from pathlib import Path
import argparse,hashlib,json,sys,inspect
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
from reference_tile import integer_difference
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
rng=np.random.default_rng(16520261019);n=8192;current=rng.integers(0,256,(n,3),dtype=np.uint8);ref=rng.integers(0,256,(n,3),dtype=np.uint8);gain=rng.integers(0,1024,(n,3),dtype=np.int32);offset=rng.integers(-2048,2048,(n,3),dtype=np.int32);edge=rng.integers(0,256,n,dtype=np.uint8);high=rng.integers(0,256,n,dtype=np.uint8);low=rng.integers(0,256,n,dtype=np.uint8)
# Explicit boundary values include strict equality and signed/clipping extremes.
for i in range(256):
 current[i]=i;ref[i]=i;gain[i]=256;offset[i]=0;edge[i]=0;high[i]=0;low[i]=0
for i in range(256,512):
 current[i]=i-256;ref[i]=128;gain[i]=256;offset[i]=[-20,0,20];edge[i]=i-256;high[i]=18;low[i]=9
normalized,score,strong,weak=integer_difference(ref,current,gain,offset,edge,high.astype(np.int16),low.astype(np.int16))
def pack(fields):
 value=0
 for number,width in fields:value=(value<<width)|(int(number)&((1<<width)-1))
 return value
inputs=[];outputs=[]
for i in range(n):
 rgb=lambda v:pack([(x,8) for x in v]);sof=int(i%97==0);eol=int(i%127==126)
 inputs.append(pack([(rgb(current[i]),24),(rgb(ref[i]),24),*[(g,10) for g in gain[i]],*[(b,12) for b in offset[i]],(edge[i],8),(high[i],8),(low[i],8),(i,32),(sof,1),(eol,1)]))
 outputs.append(pack([(rgb(normalized[i]),24),(score[i],8),(strong[i],1),(weak[i],1),(i,32),(sof,1),(eol,1)]))
for name,values,width in [('input.mem',inputs,43),('expected.mem',outputs,17)]:
 (a.out/name).write_text(''.join(f'{v:0{width}x}\n' for v in values))
proof=dict(vectors=n,seed=16520261019,scope='Pixel arithmetic only; full signed offset/gain ranges, no registration/DDR/board proof',oracle_function_sha256=hashlib.sha256(inspect.getsource(integer_difference).encode()).hexdigest(),rtl_sha256=hashlib.sha256((ROOT/'experimental/reference_v165/rtl/reference_difference_v165.v').read_bytes()).hexdigest(),testbench_sha256=hashlib.sha256((ROOT/'sim/tb_reference_difference_v165.sv').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.iterdir()})
(a.out/'manifest.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
