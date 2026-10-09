from pathlib import Path
import hashlib,json,subprocess,re,difflib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_20';W=R/(R.name+'.sdk');O=R/'reports/v132'
T=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
text=subprocess.check_output([str(T/'arm-none-eabi-objdump.exe'),'-d',str(elf)],text=True);(O/'firmware_disassembly.txt').write_text(text)
def body(name):return re.search(r'<'+re.escape(name)+r'>:\n(.*?)(?=\n[0-9a-f]+ <)',text,re.S).group(1)
irq=body('IRQHandler')
for op in [r'vpush\s+\{d0-d7\}',r'vpush\s+\{d16-d31\}',r'vmrs\s+r1, fpscr',r'vmrs\s+r1, fpexc',r'vmsr\s+fpexc, r1',r'vmsr\s+fpscr, r1',r'vpop\s+\{d16-d31\}',r'vpop\s+\{d0-d7\}']:assert re.search(op,irq),op
assert not re.search(r'\t(v[a-z][a-z0-9.]*)\s',body('memcpy'))
assert body('tile_capture_health')
symbols=subprocess.check_output([str(T/'arm-none-eabi-nm.exe'),'-n',str(elf)],text=True)
names={m[2]:int(m[0],16) for l in symbols.splitlines() if len(m:=l.split())==3}
assert names['__irq_stack']-names['_irq_stack_end']==4096
plan=read(R/'ITERATION_PLAN.json');hardware={k:sha(W/k) for k in plan['inherited_hardware_sha256']};assert hardware==plan['inherited_hardware_sha256']
for folder in ('rtl','constraints'):
 for p in (R/folder).rglob('*'):
  if p.is_file():assert sha(p)==sha(B/p.relative_to(R)),p
native=read(O/'health_native.json');assert native['passed'] and sha(W/'ethernet_sources/capture_health.h')==native['health_header_sha256'] and sha(W/'ethernet_sources/main.c')==native['main_sha256']
recovery=read(O/'dma_recovery_native.json');assert recovery['passed'] and recovery['main_sha256']==native['main_sha256'] and recovery['recovery_header_sha256']==sha(W/'ethernet_sources/dma_recovery.h')
changed=[];diff=[];bw=B/(B.name+'.sdk')/'ethernet_sources'
for p in (W/'ethernet_sources').iterdir():
 if not p.is_file():continue
 assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p
 old=(bw/p.name).read_text() if (bw/p.name).exists() else '';new=p.read_text()
 if p.name not in ('event_queue.h','main.c','network.c','capture_health.h','dma_recovery.h','event_identity.h'):assert old==new,p.name
 if p.name=='event_queue.h':
  expected=old.replace('0x00011400u','0x00011500u')
  assert new==expected,'Queue ownership/ACK path unexpectedly changed'
 if old!=new:
  changed.append(p.name);diff.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='V1.20/'+p.name,tofile='V1.21/'+p.name))
(O/'firmware_changes.diff').write_text(''.join(diff))
result=dict(passed=True,elf_sha256=sha(elf),irq_fp_saved=True,irq_stack_bytes=4096,integer_memcpy_preserved=True,hardware_sha256=hardware,queue_ack_unchanged=True,
            source_changes=changed,identity_header_sha256=sha(W/'ethernet_sources/event_identity.h'),recovery_header_sha256=recovery['recovery_header_sha256'],health_header_sha256=native['health_header_sha256'],main_sha256=native['main_sha256'],build_script_sha256=sha(W/'build_ethernet.py'),irq_instructions=irq)
(O/'firmware_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='irq_instructions'}))
