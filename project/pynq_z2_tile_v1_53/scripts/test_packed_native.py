"""Compile exact firmware encoder; test independent layout and bounded work."""
from pathlib import Path
import subprocess,ctypes,json,sys,hashlib
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/native_packed';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'));from packed_pixels import decode
h=R/(R.name+'.sdk')/'ethernet_sources/packed_pixels.h'
c=O/'wrapper.c';c.write_text('#include "'+h.as_posix()+'''"
__declspec(dllexport) int run(const uint32_t *src,uint32_t n,void *dst,uint32_t cap,uint32_t step){
 PackedPixels s;uint32_t old;packed_begin(&s,src,n,dst,cap);
 if(!step)return -3;
 while(!s.done){old=s.pos;packed_feed(&s,src+s.pos,step);if(s.pos-old>step)return -2;}
 return s.failed?-1:(int)s.bytes;
}
''')
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
subprocess.run([gcc,'-shared','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(O/'packed.dll')],check=True)
dll=ctypes.CDLL(str(O/'packed.dll'));f=dll.run;f.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32];f.restype=ctypes.c_int
rng=np.random.default_rng(125);checks=0;guard=0;bad=0
sizes=list(range(0,35))+[255,256,257,2047,2048,2049,921600]
for n in sizes:
 a=rng.integers(0,1<<25,n,dtype=np.uint32);expected=n*3+(n+7)//8
 raw=a.tobytes();pixels=np.frombuffer(raw,np.uint8).reshape(n,4)
 wire=pixels[:,:3].copy().tobytes()+np.packbits(pixels[:,3],bitorder='little').tobytes()
 assert len(wire)==expected
 for step in (1,3,4,7,8,31,2048):
  out=np.full(expected+16,0xab,np.uint8);got=f(a.ctypes.data,n,out.ctypes.data,expected,step)
  assert got==expected and out[:got].tobytes()==wire
  assert np.all(out[expected:]==0xab);assert decode(out[:got],n*4)==raw;checks+=1
  if n:
   out.fill(0xab);assert f(a.ctypes.data,n,out.ctypes.data,expected-1,step)==-1
   assert np.all(out==0xab);guard+=1
   out.fill(0xab);assert f(a.ctypes.data,n,out.ctypes.data+1,expected,step)==-1
   assert np.all(out==0xab);guard+=1
 for bit in range(25,32):
  if not n:continue
  for ix in {0,n//2,n-1}:
   b=a.copy();b[ix]|=np.uint32(1<<bit);out=np.full(expected+16,0xab,np.uint8)
   assert f(b.ctypes.data,n,out.ctypes.data,expected,2048)==-1
   assert np.all(out[expected:]==0xab);bad+=1
result=dict(passed=True,layout_roundtrips=checks,capacity_alignment_rejections=guard,noncanonical_rejections=bad,header_sha256=hashlib.sha256(h.read_bytes()).hexdigest(),scope='Actual optimized C encoder; independent NumPy wire layout, strict decoder, output guards and incremental budgets')
(O/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
