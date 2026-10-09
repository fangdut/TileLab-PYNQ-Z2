from pathlib import Path
import numpy as np,ctypes,subprocess,json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/native_probe';O.mkdir(parents=True,exist_ok=True)
h=R/'pynq_z2_tile_v1_53.sdk/ethernet_sources/rle_probe.h'
(O/'wrapper.c').write_text('#include "'+h.as_posix()+'"\n__declspec(dllexport) unsigned probe(const uint32_t*p,unsigned n){return tile_rle_worthwhile(p,n);}\n')
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
subprocess.run([gcc,'-shared','-O2','-Wall','-Wextra','-Werror','-fno-builtin-memcpy',str(O/'wrapper.c'),str(R/'pynq_z2_tile_v1_53.sdk/ethernet_sources/safe_memcpy.c'),'-o',str(O/'probe.dll')],check=True)
f=ctypes.CDLL(str(O/'probe.dll')).probe;f.argtypes=[ctypes.c_void_p,ctypes.c_uint];f.restype=ctypes.c_uint
rng=np.random.default_rng(1801);results=[]
for n in [1,15,16,17,31,64,921600]:
 for case in range(40):
  a=rng.integers(0,2**32,n,dtype=np.uint32)
  if case%4==0:a[:]=123
  elif case%4==1:a[:int(n*.75)]=0
  expected=False
  if n>=16:
   count=0
   for i in range(64):
    off=((i*15317+9011)%(n-15))&~7
    assert 0<=off and off+16<=n
    block=a[off:off+16];count+=int(np.count_nonzero(block[1:]==block[:-1]))
   expected=count>=480
  assert bool(f(a.ctypes.data,n))==expected
  if n==921600 and case%4==0:assert expected
  if n==921600 and case%4>=2:assert not expected
  results.append(dict(words=n,case=case,probe=expected))
summary=dict(passed=True,cases=len(results),scope='Exact firmware probe vs independent NumPy sampling; input bounds and deterministic noise bypass')
(O/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
