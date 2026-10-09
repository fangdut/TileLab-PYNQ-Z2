"""Inspect actual linked code and unchanged hardware, not source promises."""
from pathlib import Path
import json,subprocess,re,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_15';W=R/(R.name+'.sdk');O=R/'reports/v132'
tool=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
text=subprocess.check_output([str(tool/'arm-none-eabi-objdump.exe'),'-d',str(elf)],text=True)
(O/'firmware_disassembly.txt').write_text(text)
def body(name):return re.search(r'<'+re.escape(name)+r'>:\n(.*?)(?=\n[0-9a-f]+ <)',text,re.S).group(1)
irq=body('IRQHandler')
for op in [r'vpush\s+\{d0-d7\}',r'vpush\s+\{d16-d31\}',r'vmrs\s+r1, fpscr',r'vmrs\s+r1, fpexc',
           r'vmsr\s+fpexc, r1',r'vmsr\s+fpscr, r1',r'vpop\s+\{d16-d31\}',r'vpop\s+\{d0-d7\}']:
 assert re.search(op,irq),op
copy=body('memcpy');assert not re.search(r'\t(v[a-z][a-z0-9.]*)\s',copy),'Integer memcpy was replaced'
nm=subprocess.check_output([str(tool/'arm-none-eabi-nm.exe'),'-n',str(elf)],text=True)
symbols={m[2]:int(m[0],16) for l in nm.splitlines() if len(m:=l.split())==3}
stack=symbols['__irq_stack']-symbols['_irq_stack_end'];assert stack==4096
plan=read(R/'ITERATION_PLAN.json');hardware={k:sha(W/k) for k in plan['inherited_hardware_sha256']}
assert hardware==plan['inherited_hardware_sha256']
unchanged=[]
for folder in ['rtl','constraints']:
 for p in (R/folder).rglob('*'):
  if p.is_file():assert sha(p)==sha(B/p.relative_to(R));unchanged.append(p.relative_to(R).as_posix())
fw_changes=[];bw=B/(B.name+'.sdk')/'ethernet_sources'
for p in (W/'ethernet_sources').iterdir():
 if p.is_file():
  old=(bw/p.name).read_text();new=p.read_text()
  expected=old.replace('0x00010f00u','0x00011000u').replace('V1.15','V1.16')
  if p.name=='lscript.ld':expected=expected.replace('_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 1024;','_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 4096;')
  assert new==expected,p.name
  if old!=new:fw_changes.append(p.name)
  assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p.name
flags=(W/'hdmi_platform/ps7_cortexa9_0/standalone_a9/bsp/bsp.yaml').read_text()
assert '-DFPU_HARD_FLOAT_ABI_ENABLED=1' in flags
result=dict(passed=True,elf_sha256=sha(elf),irq_fp_saved=True,irq_instructions=irq,
            irq_entry_bytes=224,additional_fp_entry_bytes=200,production_irq_stack_bytes=stack,
            integer_memcpy_preserved=True,hardware_sha256=hardware,unchanged_rtl_constraints=unchanged,
            firmware_source_changes=fw_changes,firmware_source_scope='Release identity and IRQ linker stack; behavior change is BSP exception vectors and linker stack',
            build_script_sha256=sha(W/'build_ethernet.py'),linker_sha256=sha(W/'hdmi_ethernet/src/lscript.ld'))
(O/'firmware_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=True,irq_fp_saved=True,irq_stack_bytes=stack,integer_memcpy_preserved=True,hardware_unchanged=True)))
