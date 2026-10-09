"""Compile the exact firmware header on the host, cross-check with Python.
Includes random chunks, long runs, short repeats, output bounds and raw fallback.
"""
from pathlib import Path
import subprocess,ctypes,json,sys,random
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/native_rle';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'));import word_rle
decode=word_rle.decode;native_decoder=word_rle._native
h=R/'pynq_z2_tile_v1_53.sdk/ethernet_sources/word_rle.h'
c=O/'wrapper.c';c.write_text('#include "'+h.as_posix()+'''"
__declspec(dllexport) int run(const uint32_t *src,uint32_t n,uint32_t *dst,uint32_t cap,uint32_t step){
 WordRle s;uint32_t old;rle_begin(&s,src,n,dst,cap);
 do{old=s.pos;rle_step(&s,step);if(s.pos-old>step)return -2;}while(!s.done);
 return s.failed?-1:(int)s.out;
}
''')
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
subprocess.run([gcc,'-shared','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(O/'rle.dll')],check=True)
dll=ctypes.CDLL(str(O/'rle.dll'));f=dll.run;u=ctypes.POINTER(ctypes.c_uint32);f.argtypes=[u,ctypes.c_uint32,u,ctypes.c_uint32,ctypes.c_uint32];f.restype=ctypes.c_int
rng=np.random.default_rng(1729);cases=[]
for n in [1,2,3,4,31,32,2047,2048,2049,921600]:
 cases += [np.zeros(n,np.uint32),rng.integers(0,2**32,n,dtype=np.uint32),np.arange(n,dtype=np.uint32)%3]
for _ in range(200):
 vals=rng.integers(0,2**32,100,dtype=np.uint32);counts=rng.integers(1,50,100);cases.append(np.repeat(vals,counts))
passed=0;fallback=0
for a in cases:
 for step in [1,7,2048]:
  cap=len(a);out=np.full(cap+2,0xaabbaabb,np.uint32)
  n=f(a.ctypes.data_as(u),len(a),out.ctypes.data_as(u),cap,step)
  assert np.all(out[cap:]==0xaabbaabb),'Output guard modified'
  if n>=0:
   for backend in [None,native_decoder]:
    word_rle._native=backend
    assert decode(out[:n].tobytes(),len(a)*4)==a.tobytes()
  else:assert n==-1;fallback+=1
  passed+=1
word_rle._native=native_decoder
res=dict(passed=True,cases=passed,raw_fallback_cases=fallback,scope='Actual firmware C encoder against Python and native host decoders; guard words and incremental work bounds')
(O/'result.json').write_text(json.dumps(res,indent=2));print(json.dumps(res))
