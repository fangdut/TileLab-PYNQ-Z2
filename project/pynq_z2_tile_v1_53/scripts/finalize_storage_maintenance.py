"""Record the maintenance state without rewriting the original hardware release."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,urllib.request

root=Path(__file__).resolve().parents[1]
out=root/'reports/storage_20260926'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
state=json.load(urllib.request.urlopen('http://127.0.0.1:8770/api/state'))
assert state['storage']['mode']=='preview' and state['enabled'] and not state['error']
write(out/'final_state.json',state)
preview=json.loads((out/'live_preview.json').read_text())
archive=json.loads((out/'live_archive.json').read_text())
assert preview['passed'] and archive['passed']
delivery=json.loads((root/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8-sig'))
board={name:digest(root/'pynq_z2_tile_v1_5.sdk'/name) for name in delivery['programming']['sha256']}
assert board==delivery['programming']['sha256']
assert state['board_stats']['boot_id']==delivery['programming']['boot_id']
parts={};count=0
for current,dirs,names in os.walk(root,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(current)/d).is_symlink() and not (Path(current)/d).is_junction()]
    for name in names:
        p=Path(current)/name
        if p.is_symlink():continue
        size=p.stat().st_size;part=p.relative_to(root).parts[0]
        parts[part]=parts.get(part,0)+size;count+=1
inventory=dict(measured_at=datetime.now(timezone.utc).isoformat(),measurement='Logical file bytes, excludes junction/symlink traversal',bytes=sum(parts.values()),files=count,parts=parts,disk_free_bytes=shutil.disk_usage(root).free,deletion_executed=False)
write(out/'storage_inventory_after.json',inventory)
files=['host/workstation.py','host/workstation.html','host/storage_policy.py','host/storage_policy.json','host/test_storage_policy.py','scripts/test_storage_live.py','scripts/cleanup_reviewed_test_data.ps1','scripts/cleanup_metadata.py','scripts/finalize_storage_maintenance.py','docs/存储维护与系统分工_20260926.md','README.md']
evidence=['live_preview.json','live_archive.json','host_tests.log','storage_ui.png','cleanup_plan.json','storage_inventory_after.json']
manifest=dict(workstation_release='1.5.1-storage',hardware_release='V1.5',created_at=datetime.now(timezone.utc).isoformat(),hardware_unchanged_verified=True,programmed_boot_id=state['board_stats']['boot_id'],hardware_sha256=board,
 original_delivery_manifest_scope='Historical V1.5 delivery snapshot; host sources have since changed',
 deletion=dict(executed=False,blocked_by='Automatic approval: blocked by policy; no further reason provided',reviewed_files=8496,reviewed_archive_records=3448,expected_released_bytes=5893401187,dry_run_passed=True,apply_phase_tested=False),
 tests=dict(unit_tests=50,unit_tests_passed=50,board_preview_passed=True,board_archive_passed=True),
 final_mode='preview',storage_cap_mib=state['storage']['max_archive_mib'],current_archive_records=state['records_total'],source_sha256={name:digest(root/name) for name in files},evidence_sha256={name:digest(out/name) for name in evidence})
write(root/'MAINTENANCE_MANIFEST.json',manifest)
print(json.dumps(dict(project_gib=round(inventory['bytes']/2**30,3),free_disk_gib=round(inventory['disk_free_bytes']/2**30,3),archive_records=state['records_total'],mode=state['storage']['mode'],board_unchanged=True,deletion_executed=False),ensure_ascii=False))
