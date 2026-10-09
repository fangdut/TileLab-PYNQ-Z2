from pathlib import Path
import subprocess,ctypes,numpy as np,json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/native_copy';O.mkdir(parents=True,exist_ok=True)
c=O/'wrapper.c';c.write_text('#include <stddef.h>\nvoid *memcpy(void*,const void*,size_t);\n__declspec(dllexport) void *copy_test(void*d,const void*s,size_t n){return memcpy(d,s,n);}\n')
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
subprocess.run([gcc,'-shared','-O2','-fno-builtin-memcpy','-Wall','-Werror',str(c),str(R/'pynq_z2_tile_v1_53.sdk/ethernet_sources/safe_memcpy.c'),'-o',str(O/'copy.dll')],check=True)
f=ctypes.CDLL(str(O/'copy.dll')).copy_test;f.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];f.restype=ctypes.c_void_p
rng=np.random.default_rng(1702);cases=0
for n in [0,1,2,3,4,7,8,15,31,32,33,63,64,127,160,272,2048,8192]:
 for so in range(8):
  for do in range(8):
   a=rng.integers(0,256,n+32,dtype=np.uint8);b=np.full(n+32,0xa7,np.uint8);before=b.copy()
   returned=f(b.ctypes.data+do,a.ctypes.data+so,n);assert returned==b.ctypes.data+do
   assert np.array_equal(a[so:so+n],b[do:do+n]) and np.array_equal(b[:do],before[:do]) and np.array_equal(b[do+n:],before[do+n:]);cases+=1
res=dict(passed=True,cases=cases,scope='Portable byte/tail path and memcpy contract; ARM LDM/STM path requires hardware byte-exact acceptance')
(O/'result.json').write_text(json.dumps(res,indent=2));print(json.dumps(res))
