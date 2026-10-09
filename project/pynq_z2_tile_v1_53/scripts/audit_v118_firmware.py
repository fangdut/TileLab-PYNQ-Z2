from pathlib import Path
import hashlib,json,subprocess,re,difflib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_17';W=R/(R.name+'.sdk');O=R/'reports/v132'
T=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
text=subprocess.check_output([str(T/'arm-none-eabi-objdump.exe'),'-d',str(elf)],text=True);(O/'firmware_disassembly.txt').write_text(text)
def body(name):return re.search(r'<'+re.escape(name)+r'>:\n(.*?)(?=\n[0-9a-f]+ <)',text,re.S).group(1)
irq=body('IRQHandler')
for op in [r'vpush\s+\{d0-d7\}',r'vpush\s+\{d16-d31\}',r'vmrs\s+r1, fpscr',r'vmrs\s+r1, fpexc',r'vmsr\s+fpexc, r1',r'vmsr\s+fpscr, r1',r'vpop\s+\{d16-d31\}',r'vpop\s+\{d0-d7\}']:assert re.search(op,irq),op
assert not re.search(r'\t(v[a-z][a-z0-9.]*)\s',body('memcpy'))
symbols=subprocess.check_output([str(T/'arm-none-eabi-nm.exe'),'-n',str(elf)],text=True)
names={m[2]:int(m[0],16) for l in symbols.splitlines() if len(m:=l.split())==3}
assert names['__irq_stack']-names['_irq_stack_end']==4096
plan=read(R/'ITERATION_PLAN.json');hardware={k:sha(W/k) for k in plan['inherited_hardware_sha256']};assert hardware==plan['inherited_hardware_sha256']
for folder in ('rtl','constraints'):
 for p in (R/folder).rglob('*'):
  if p.is_file():assert sha(p)==sha(B/p.relative_to(R)),p
native=read(O/'ack_isolation_native.json');assert native['passed'] and sha(W/'ethernet_sources/event_queue.h')==native['candidate_header_sha256']
changed=[];diff=[];bw=B/(B.name+'.sdk')/'ethernet_sources'
for p in (W/'ethernet_sources').iterdir():
 if not p.is_file():continue
 assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p
 old=(bw/p.name).read_text();new=p.read_text();expected=old.replace('V1.17','V1.18')
 if p.name=='network.c':expected=expected.replace(' }else if(rx[1]==2 && rx[2]==queue.meta[M_BOOT] && (rx[3]==queue.head || rx[3]==queue.head+1)){\n  if(rx[3]!=queue.head){queue.meta[M_ACK]=rx[3];queue_ack(&queue);}\n  reply(queue.head==rx[3]?1:2,0);',' }else if(rx[1]==2){\n  /* Reject future/stale/wrong-boot requests before touching the ACK mailbox.\n   * A duplicate committed head is harmless; the next ID needs a real front. */\n  if(rx[2]!=queue.meta[M_BOOT] || (rx[3]!=queue.head && (queue.head==queue.tail || rx[3]!=queue.head+1))){\n   queue.meta[M_ACK_ERRORS]++;reply(2,0);\n  }else{\n   if(rx[3]!=queue.head){queue.meta[M_ACK]=rx[3];queue_ack(&queue);}\n   reply(queue.head==rx[3]?1:2,0);\n  }')
 if p.name!='event_queue.h':assert new==expected,p.name
 if old!=new:
  changed.append(p.name);diff.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='V1.17/'+p.name,tofile='V1.18/'+p.name))
(O/'firmware_changes.diff').write_text(''.join(diff))
result=dict(passed=True,elf_sha256=sha(elf),irq_fp_saved=True,irq_stack_bytes=4096,integer_memcpy_preserved=True,hardware_sha256=hardware,
            source_changes=changed,queue_header_sha256=native['candidate_header_sha256'],build_script_sha256=sha(W/'build_ethernet.py'),irq_instructions=irq)
(O/'firmware_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='irq_instructions'}))
