"""Verify this host-only release preserved the validated PL and firmware logic."""
from pathlib import Path
import json,hashlib,subprocess,re,difflib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_28';W=R/(R.name+'.sdk');BW=B/(B.name+'.sdk');O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
baseline=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json')
for name,h in baseline['source_sha256'].items():assert sha(B/name)==h,name
assert sha(Path(plan['backup']))==plan['backup_sha256']
hardware={name:sha(W/name) for name in plan['inherited_hardware_sha256']};assert hardware==plan['inherited_hardware_sha256']
for folder in ('rtl','constraints'):
    for p in (R/folder).rglob('*'):
        if p.is_file():assert sha(p)==sha(B/p.relative_to(R)),p
changes=[];diff=[];sources={}
for p in (W/'ethernet_sources').iterdir():
    if not p.is_file():continue
    old=(BW/'ethernet_sources'/p.name).read_text();new=p.read_text()
    expected=old.replace('V1.28','V1.29').replace('0x00011c00u','0x00011d00u')
    assert new==expected,'Unexpected firmware behavior change: '+p.name
    assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),'Build source mismatch'
    sources[p.name]=sha(p)
    if old!=new:changes.append(p.name);diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='V1.28/'+p.name,tofile='V1.29/'+p.name))
(O/'firmware_changes.diff').write_text(''.join(diff))
T=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin');elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
text=subprocess.check_output([str(T/'arm-none-eabi-objdump.exe'),'-d',str(elf)],text=True)
def body(name):return re.search(r'<'+re.escape(name)+r'>:\n(.*?)(?=\n[0-9a-f]+ <)',text,re.S).group(1)
irq=body('IRQHandler')
for op in [r'vpush\s+\{d0-d7\}',r'vpush\s+\{d16-d31\}',r'vmrs\s+r1, fpscr',r'vmrs\s+r1, fpexc',r'vmsr\s+fpexc, r1',r'vmsr\s+fpscr, r1',r'vpop\s+\{d16-d31\}',r'vpop\s+\{d0-d7\}']:assert re.search(op,irq),op
assert not re.search(r'\t(v[a-z][a-z0-9.]*)\s',body('memcpy'))
symbols=subprocess.check_output([str(T/'arm-none-eabi-nm.exe'),'-n',str(elf)],text=True)
names={m[2]:int(m[0],16) for l in symbols.splitlines() if len(m:=l.split())==3}
assert names['__irq_stack']-names['_irq_stack_end']==4096
result=dict(passed=True,source_changes=changes,source_changes_only_version_and_comments=True,source_sha256=sources,hardware_sha256=hardware,
    baseline_source_files_verified=len(baseline['source_sha256']),baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),backup_sha256=plan['backup_sha256'],
    elf_sha256=sha(elf),irq_fp_saved=True,irq_stack_bytes=4096,integer_memcpy_preserved=True,irq_instructions=irq,
    scope='New full Vitis build and executable audit; no PL logic change or new synthesis claim. Prior transport fault results remain baseline evidence, not newly repeated tests.')
(O/'firmware_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','irq_instructions')}))
