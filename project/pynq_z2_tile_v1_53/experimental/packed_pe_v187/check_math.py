"""Exhaust exact shared-input packing and nearest square ranges offline."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).with_name('check_math.cpp');exe=a.out/'check.exe';started=time.monotonic()
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static',str(source),'-o',str(exe)],check=True,timeout=120)
    result=subprocess.run([str(exe)],capture_output=True,text=True,check=True,timeout=120);values=json.loads(result.stdout)
    j=dict(scope='INDEPENDENT_EXHAUSTIVE_PACKING_ARITHMETIC_NOT_RTL_OR_DETECTOR',passed=True,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),**values,elapsed_seconds=time.monotonic()-started,
        integrated_into_detector=False,board_programmed=False,fpga_throughput_measured=False)
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
