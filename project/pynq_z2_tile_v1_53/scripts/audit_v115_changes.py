from pathlib import Path
import hashlib,difflib,json
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_14';O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changed=[];diff=[]
for folder in ['rtl','constraints']:
 for p in sorted((R/folder).rglob('*')):
  if p.is_file():
   old=B/p.relative_to(R);assert old.is_file(),p
   if sha(p)!=sha(old):
    changed.append(p.relative_to(R).as_posix())
    diff.extend(difflib.unified_diff(old.read_text().splitlines(keepends=True),p.read_text().splitlines(keepends=True),fromfile='V1.14/'+p.relative_to(R).as_posix(),tofile='V1.15/'+p.relative_to(R).as_posix()))
assert changed==['rtl/frame_capture_sg.v'],changed
fw=R/(R.name+'.sdk')/'ethernet_sources';oldfw=B/(B.name+'.sdk')/'ethernet_sources';fw_changed=[];format_only=[]
for p in sorted(fw.iterdir()):
 if p.is_file() and sha(p)!=sha(oldfw/p.name):
  if p.read_text()==(oldfw/p.name).read_text():
   format_only.append(p.name);continue
  fw_changed.append(p.name)
  expected=(oldfw/p.name).read_text().replace('0x00010e00u','0x00010f00u').replace('V1.14','V1.15')
  assert p.read_text()==expected,(p.name,''.join(difflib.unified_diff(expected.splitlines(keepends=True),p.read_text().splitlines(keepends=True))))
assert 'event_queue.h' in fw_changed
for name in ('tcp_transport.py','confirmation_journal.py','storage_policy.py','recovery.py'):
 assert (R/'host'/name).read_text()==(B/'host'/name).read_text(),name
result=dict(passed=True,rtl_constraints_changed=changed,firmware_changes=fw_changed,firmware_change_scope='Version literal 0x00010e00 to 0x00010f00 and V1.14 to V1.15 banner/comments only',firmware_line_ending_only=format_only,unchanged_host_protocol_and_journal=True,baseline_rtl_sha256=sha(B/'rtl/frame_capture_sg.v'),new_rtl_sha256=sha(R/'rtl/frame_capture_sg.v'))
(O/'change_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(O/'rtl_changes.diff').write_text(''.join(diff),encoding='utf-8')
print(json.dumps(result))
