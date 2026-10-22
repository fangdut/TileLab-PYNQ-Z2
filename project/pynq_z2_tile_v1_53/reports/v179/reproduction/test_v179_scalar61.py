from pathlib import Path
import hashlib,json,subprocess,shutil,time
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
source=P/'experimental/texture_v170/hls/frozen/v170_hls61.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,count,token in [('bilinear',131248,'BOUNDED_BILINEAR_SCALAR_PASS'),('normalize',100072,'SEGMENTED_NORMALIZATION_SCALAR_PASS'),('requant',100088,'REQUANT')]:
    out=W/('v179_scalar61_'+name);out.mkdir(exist_ok=False)
    harness=P/('experimental/resources_v179/test_'+name+'.cpp')
    shutil.copy2(source,out/'kernel.cpp');shutil.copy2(harness,out/'test.cpp');start=time.monotonic()
    with (out/'compile.log').open('w') as log:
        subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(out/'test.cpp'),'-o',str(out/'test.exe')],stdout=log,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(out/'test.exe')],capture_output=True,text=True,check=True);(out/'test.log').write_text(r.stdout+r.stderr)
    assert token in r.stdout and str(count) in r.stdout,r.stdout
    j=dict(scope='INDEPENDENT_SCALAR_C_NOT_RTL_OR_BOARD',passed=True,cases=count,source_sha256=sha(source),harness_sha256=sha(harness),elapsed_seconds=time.monotonic()-start,output=r.stdout.strip())
    (out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j),flush=True)
