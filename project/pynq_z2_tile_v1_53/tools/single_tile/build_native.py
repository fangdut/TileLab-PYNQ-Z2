"""Optional accelerator; explicit compiler, new output only, no model training."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--compiler',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();source=Path(__file__).with_name('fine_integer_native.c')
if a.out.exists():raise FileExistsError(a.out)
a.out.parent.mkdir(parents=True,exist_ok=True)
cmd=[a.compiler,'-O2','-std=c11','-shared']
cmd+=['-static-libgcc'] if os.name=='nt' else ['-fPIC']
subprocess.run(cmd+[str(source),'-o',str(a.out)],check=True)
print(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest())))
