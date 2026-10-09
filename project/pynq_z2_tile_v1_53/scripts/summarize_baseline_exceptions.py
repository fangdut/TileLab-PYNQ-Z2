"""Inventory constraints for later review; no design edits or passing claims."""
from pathlib import Path
import json, re, hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
p=O/'baseline_applied.xdc'
context='';entries=[]
for line in p.read_text().splitlines():
    if line.startswith('current_instance '):context=line[len('current_instance '):]
    if line.startswith(('set_clock_groups ','set_max_delay ','set_bus_skew ')):
        entries.append(dict(context=context,constraint=line))
ignored=(O/'baseline_ignored_exceptions.rpt').read_text()
overridden=[]
for line in ignored.splitlines():
    if re.match(r'^\d+\s',line) and 'Totally overridden path by CG' in line:
        overridden.append(dict(position=int(line.split()[0]),line=line.rstrip()))
methodology=(R/'reports/methodology.rpt').read_text()
assert 'pynq_z2_tile_v1_24/reports/methodology.rpt' in methodology
assert '| TIMING-24 ' in methodology
result=dict(scope='Read-only V1.24 routed baseline audit for later constraint review. V1.31 detector/top constraints are unchanged; this does not constitute a fix.',
            checkpoint='D:/Vivado/pynq_z2_tile_v1_24/pynq_z2_tile_v1_24.runs/impl_1/system_wrapper_routed.dcp',
            baseline_max_delay_overridden_warnings=8,entries=entries,overridden=overridden,
            sources_sha256={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'baseline_exception_inventory.json').write_text(json.dumps(result,indent=2))
for entry in entries:
    if entry['constraint'].startswith('set_max_delay') and 'dbg_hub' not in entry['constraint'] and 'BSCANID' not in entry['constraint']:
        print(entry['context'],entry['constraint'])
print('Clock-group-overridden exception rows:',len(overridden))
