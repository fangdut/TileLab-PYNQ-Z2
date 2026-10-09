"""Read-only audit of the already accepted baseline ELF; no firmware changes."""
from pathlib import Path
import subprocess,re,hashlib,json,sys
R=Path(__file__).resolve().parents[1];minor=int(sys.argv[1]) if len(sys.argv)>1 else 14
assert minor in (14,15),'Only the verified baseline and current release are audit targets'
B=R.parent/f'pynq_z2_tile_v1_{minor}';W=B/(B.name+'.sdk');O=R/'reports/v132/irq_audit';O.mkdir(exist_ok=True)
tag=f'v1{minor}';release=f'V1.{minor}'
elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
tool=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin/arm-none-eabi-objdump.exe')
text=subprocess.check_output([str(tool),'-d',str(elf)],text=True,encoding='utf-8',errors='replace')
(O/f'{tag}_disassembly.txt').write_text(text,encoding='utf-8')
functions={};current=None
for line in text.splitlines():
 m=re.match(r'^([0-9a-f]+) <([^>]+)>:',line)
 if m:current=m[2];functions[current]=[]
 elif current:functions[current].append(line)
vfp={}
for name,lines in functions.items():
 hits=[l.strip() for l in lines if re.search(r'\t(v[a-z][a-z0-9]*(?:\.[a-z0-9]+)?)\s',l)]
 if hits:vfp[name]=hits
irq='\n'.join(functions['IRQHandler']);(O/f'{tag}_irq_handler.txt').write_text(irq,encoding='utf-8')
config=W/'hdmi_platform/ps7_cortexa9_0/standalone_a9/bsp/include/bspconfig.h'
config_text=config.read_text();(O/f'{tag}_bspconfig.txt').write_text(config_text,encoding='utf-8')
result=dict(release=release,elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),irq_saves_vfp=bool(re.search(r'\bvpush\b',irq)),irq_instructions=irq,linked_vfp_functions=vfp,scope='Read-only static inventory; linked instructions are not a reachability proof; no claim every interrupt/library path has been exercised')
(O/f'{tag}_irq_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(release=release,irq_saves_vfp=result['irq_saves_vfp'],vfp_functions={k:len(v) for k,v in vfp.items()})))
