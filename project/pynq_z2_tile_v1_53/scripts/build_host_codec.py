from pathlib import Path
import subprocess,hashlib,json
R=Path(__file__).resolve().parents[1]
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
source=R/'host/native/rle_decode.c';output=R/'host/rle_decode.dll'
subprocess.run([gcc,'-shared','-O3','-Wall','-Wextra','-Werror',str(source),'-o',str(output)],check=True)
(R/'reports/v132/host_codec_build.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),compiler=gcc),indent=2))
print('Optional Windows x64 decoder built; Python fallback remains available')
