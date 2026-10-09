from pathlib import Path
import subprocess,ctypes,zlib,random,struct,json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/header_crc_native';O.mkdir(parents=True,exist_ok=True)
source=R/'pynq_z2_tile_v1_53.sdk/ethernet_sources/header_crc.h'
(O/'test.c').write_text('#include "header_crc.h"\n__declspec(dllexport) uint32_t check(const uint32_t *p,size_t n){return tile_header_crc(p,n);}\n')
cmd=['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe','-std=c11','-O2','-shared','-I'+str(source.parent),str(O/'test.c'),'-o',str(O/'test.dll')]
r=subprocess.run(cmd,capture_output=True,text=True);(O/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
dll=ctypes.CDLL(str(O/'test.dll'));f=dll.check;f.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t];f.restype=ctypes.c_uint32
rng=random.Random(112);checks=0
for n in [0,1,2,67,68,69,128]+[rng.randrange(129) for _ in range(993)]:
 for style in ('zero','one','random'):
  a=[0 if style=='zero' else 0xffffffff if style=='one' else rng.getrandbits(32) for _ in range(n)]
  raw=struct.pack('<'+str(n)+'I',*a);buf=(ctypes.c_uint32*n)(*a)
  assert f(buf,n)==zlib.crc32(raw),(n,style);checks+=1
result=dict(passed=True,cases=checks,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Actual C header function compiled natively, compared with independent zlib; ARM integration is a separate board test')
(R/'reports/v132/header_crc_native.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
