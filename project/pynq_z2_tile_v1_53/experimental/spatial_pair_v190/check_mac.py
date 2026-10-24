"""Exercise the actual integrated MAC against an independent scalar oracle."""
from pathlib import Path
import subprocess,hashlib,json,argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
for name in ['test_mac.cpp','texture_spatial_pair.cpp']:(a.out/name).write_bytes((root/name).read_bytes())
exe=a.out/'test_mac.exe'
with (a.out/'compile.log').open('w') as log:
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O2','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(a.out/'test_mac.cpp'),'-o',str(exe)],stdout=log,stderr=subprocess.STDOUT,check=True)
r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
(a.out/'run.log').write_text(r.stdout+r.stderr)
proof=dict(scope='SPATIAL_INTEGRATED_MAC_NATIVE_C_SCALAR_REFERENCE_NOT_RTL_OR_BOARD',passed=r.returncode==0 and 'SPATIAL_INTEGRATED_MAC_SCALAR_PASS' in r.stdout,source_sha256=hashlib.sha256((root/'texture_spatial_pair.cpp').read_bytes()).hexdigest(),output=r.stdout)
(a.out/'summary.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if not proof['passed']:raise SystemExit(2)
