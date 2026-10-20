"""OFFLINE verification, never used by the board workstation.

Compile the HLS arithmetic with ordinary unsigned shape types (all accepted
production dimensions fit 11 bits), then compare a real-photo full graph with
the frozen Torch reference. This does NOT establish RTL/board correctness.
"""
from pathlib import Path
import argparse,json,subprocess,hashlib,time
import numpy as np
from PIL import Image
RUNNER=r'''
#include <cstdint>
#include <cstdio>
#include <vector>
#include <fstream>
void texture_infer(const uint32_t*,uint32_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
std::vector<uint32_t> read(const char *p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)throw 1;size_t n=f.tellg();f.seekg(0);std::vector<uint32_t> v(n/4);f.read((char*)v.data(),n);return v;}
int main(int argc,char **argv){
 if(argc!=6)return 1;auto m=read(argv[1]),rgb=read(argv[2]);unsigned w=std::stoul(argv[4]),h=std::stoul(argv[5]);
 std::vector<uint32_t> work(m[17]),result(16+m[4]*m[4]+w*h);
 texture_infer(m.data(),work.data(),rgb.data(),result.data(),w,h);
 std::ofstream o(argv[3],std::ios::binary);o.write((char*)result.data(),result.size()*4);
 printf("Full C graph returned status=%u alarm=%u steps=%u\n",result[1],result[2],result[8]);return result[1]?2:0;
}
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    s=a.source.read_text();old='#include <ap_int.h>\ntypedef ap_uint<11> dim_t;\ntypedef ap_uint<17> tile_t;'
    if old not in s:raise RuntimeError('Unexpected shape types')
    (a.out/'arithmetic.cpp').write_text(s.replace(old,'typedef unsigned dim_t;\ntypedef unsigned tile_t;'))
    (a.out/'runner.cpp').write_text(RUNNER)
    compiler='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe'
    exe=a.out/'full_graph.exe'
    subprocess.run([compiler,'-O3','-std=c++17','-ffp-contract=off','-static','-Wno-unknown-pragmas',str(a.out/'arithmetic.cpp'),str(a.out/'runner.cpp'),'-o',str(exe)],check=True)
    with Image.open(a.image) as im:rgb=np.array(im.convert('RGB'),dtype=np.uint32)
    height,width=rgb.shape[:2];packed=((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4');packed.tofile(a.out/'input.bin')
    start=time.perf_counter();subprocess.run([str(exe),str(a.model/'model.bin'),str(a.out/'input.bin'),str(a.out/'result.bin'),str(width),str(height)],check=True)
    result=np.fromfile(a.out/'result.bin',dtype='<u4');scores=result[16:16+56*56].view('<f4').reshape(56,56);reference=np.load(a.model/(a.image.stem+'_scores.npy'))
    err=float(np.max(np.abs(scores-reference)))
    record=dict(scope='OFFLINE_C_ARITHMETIC_ONLY_NOT_BOARD',image=str(a.image),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),max_grid_error=err,wall_seconds=time.perf_counter()-start,alarm=int(result[2]),peak=float(result[3:4].view('<f4')[0]),reference_peak=float(reference.max()))
    (a.out/'check.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
    if err>1e-3:raise RuntimeError('Full real-photo C arithmetic differs from frozen reference')
if __name__=='__main__':main()
