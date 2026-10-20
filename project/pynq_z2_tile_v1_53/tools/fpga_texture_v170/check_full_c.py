"""Run unchanged HLS C++ against a frozen real-photo integer reference.

Offline only. This establishes neither FPGA timing nor RTL correctness.
"""
from pathlib import Path
import argparse,subprocess,time,json
import numpy as np
from PIL import Image
from evaluate_lightweight import sha,save

RUNNER=r'''
#include <stdint.h>
#include <cstdio>
#include <vector>
#include <fstream>
#include <ap_int.h>
typedef ap_uint<128> pack_t;
void texture_integer(const uint64_t*,pack_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
template<typename T>std::vector<T> load(const char*p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)throw 1;size_t n=f.tellg();f.seekg(0);std::vector<T>v(n/sizeof(T));f.read((char*)v.data(),n);return v;}
int main(int argc,char**argv){if(argc!=6)return 1;auto m=load<uint64_t>(argv[1]);auto rgb=load<uint32_t>(argv[2]);
unsigned w=std::stoul(argv[4]),h=std::stoul(argv[5]);auto header=(uint32_t*)m.data();std::vector<pack_t> work(header[16]/16);std::vector<uint32_t> out(16+header[4]*header[4]+w*h);
texture_integer(m.data(),work.data(),rgb.data(),out.data(),w,h);std::ofstream f(argv[3],std::ios::binary);f.write((char*)out.data(),out.size()*4);printf("status=%u alarm=%u peak=%u tasks=%u\n",out[1],out[2],out[3],out[8]);return out[1]?2:0;}
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--image',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'kernel.cpp').write_bytes(a.source.read_bytes());(a.out/'runner.cpp').write_text(RUNNER)
    exe=a.out/'check.exe';compiler='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe'
    subprocess.run([compiler,'-O3','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(a.out/'kernel.cpp'),str(a.out/'runner.cpp'),'-o',str(exe)],check=True)
    with Image.open(a.image) as im:rgb=np.array(im.convert('RGB'),dtype='<u4')
    height,width=rgb.shape[:2];((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4').tofile(a.out/'input.bin')
    started=time.perf_counter();subprocess.run([str(exe),str(a.profile/'model.bin'),str(a.out/'input.bin'),str(a.out/'result.bin'),str(width),str(height)],check=True)
    result=np.fromfile(a.out/'result.bin',dtype='<u4');grid=int(result[5]);actual=result[16:16+grid*grid].reshape(grid,grid)
    expected=np.load(a.profile/(a.image.stem+'_scores.npy'),allow_pickle=False)
    error=int(np.max(np.abs(actual.astype('i8')-expected)))
    record=dict(scope='OFFLINE_FULL_INTEGER_C_NOT_RTL_OR_BOARD',source_sha256=sha(a.source),model_sha256=sha(a.profile/'model.bin'),
        image_sha256=sha(a.image),max_grid_error=error,alarm=int(result[2]),peak=int(result[3]),threshold=int(result[4]),
        mask_pixels=int(result[6]),steps=int(result[8]),elapsed_seconds=time.perf_counter()-started)
    save(a.out/'check.json',record);print(json.dumps(record),flush=True)
    if error:raise RuntimeError('Integer C++ differs from frozen reference')
if __name__=='__main__':main()
