from pathlib import Path
import json,hashlib,zipfile,difflib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_31';O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json')
assert all(sha(B/n)==h for n,h in old['source_sha256'].items())
assert sha(Path(plan['backup']))==plan['backup_sha256']
with zipfile.ZipFile(plan['backup']) as z:
 saved=json.loads(z.read('BACKUP_HASHES.json'))
 for n,h in old['source_sha256'].items():
  assert saved[n]==h and hashlib.sha256(z.read(n)).hexdigest()==h,n
for folder in ('rtl','ip_repo'):
 for p in (B/folder).rglob('*'):
  if p.is_file():assert sha(p)==sha(R/p.relative_to(B)),p
before=(B/'constraints/pynq_z2.xdc').read_text();after=(R/'constraints/pynq_z2.xdc').read_text()
commands=lambda s:[l.strip() for l in s.splitlines() if l.strip() and not l.strip().startswith('#')]
removed=[l for l in commands(before) if l not in commands(after)]
assert len(removed)==1 and removed[0].startswith('set_clock_groups -asynchronous')
assert commands(after)==[l for l in commands(before) if l not in removed]
assert 'create_waiver' not in (R/'scripts/create_project.tcl').read_text()
generated={}
for name in ('SyncBase.vhd','DecoderResetDomains.vhd','TMDS_Decoder.vhd','dvi2rgb.vhd'):
 candidates=[p for p in (R/(R.name+'.gen')/'sources_1/bd/system/ipshared').rglob(name) if sha(p)==sha(R/'ip_repo/dvi2rgb_v1_7/src'/name)]
 assert len(candidates)==1,(name,candidates)
 generated[candidates[0].relative_to(R).as_posix()]=sha(candidates[0])
p=R/(R.name+'.gen')/'sources_1/bd/system/ip/system_hdmi_rx_0/src/dvi2rgb.xdc'
assert sha(p)==sha(R/'ip_repo/dvi2rgb_v1_7/src/dvi2rgb.xdc');generated[p.relative_to(R).as_posix()]=sha(p)
(O/'constraint_changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='V1.31/pynq_z2.xdc',tofile='V1.32/pynq_z2.xdc')))
result=dict(passed=True,baseline_source_files=len(old['source_sha256']),backup_sha256=plan['backup_sha256'],detector_rtl_unchanged=True,ip_sources_unchanged=True,removed_clock_groups=removed,new_false_paths_or_waivers=0,authored_changes_sha256={'constraints/pynq_z2.xdc':sha(R/'constraints/pynq_z2.xdc')},generated_ip_sources_sha256=generated,scope='Fresh source/generated-IP/backup audit. V1.31 reset simulation inherited because RTL and IP are byte-identical; V1.32 implementation and board tests are separate fresh evidence.')
cursor_lines='# The HDMI stimulus must not contain a desktop pointer over the test image.\n# Local to this window: the pointer remains visible on the operator\'s desktop.\n$w.Cursor=[System.Windows.Input.Cursors]::None;$w.ForceCursor=$true\n'
player=(R/'host/hdmi_display.ps1').read_text(encoding='utf-8-sig')
assert player.count(cursor_lines)==1 and player.replace(cursor_lines,'')==(B/'host/hdmi_display.ps1').read_text(encoding='utf-8-sig')
result['stimulus_change']='Hide pointer only within HDMI stimulus window; no image scaling, timing or source-content change.'
result['authored_changes_sha256']['host/hdmi_display.ps1']=sha(R/'host/hdmi_display.ps1')
(O/'source_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
