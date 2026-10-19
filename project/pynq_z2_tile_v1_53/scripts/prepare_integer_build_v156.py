"""Prepare a fresh isolated Vivado folder without changing the frozen source."""
from pathlib import Path
import argparse,shutil,json,hashlib
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();B=args.out.resolve()
if B.exists():raise FileExistsError('Choose a new build folder')
profile=json.loads((R/'models/v156_frozen_profile.json').read_text())
for rel,digest in profile['source_sha256'].items():
    if hashlib.sha256((R/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Frozen algorithm changed: '+rel)
B.mkdir(parents=True)
for folder in ['rtl','constraints','ip_repo','scripts']:shutil.copytree(R/folder,B/folder)
S=B/'pynq_z2_tile_v1_53.sdk';S.mkdir();A=R/'pynq_z2_tile_v1_53.sdk'
shutil.copytree(A/'ethernet_sources',S/'ethernet_sources');shutil.copy2(A/'build_ethernet.py',S/'build_ethernet.py')
(B/'reports/v156').mkdir(parents=True);(B/'tmp').mkdir();(B/'CANDIDATE_BUILD_ONLY').write_text('V1.56 isolated build; never program hardware.\n')
shutil.copy2(R/'models/v156_frozen_profile.json',B/'reports/v156/frozen_profile.json')
p=B/'scripts/create_project.tcl';s=p.read_text();old='source $root/scripts/add_capture.tcl\nvalidate_bd_design'
assert old in s;s=s.replace(old,'''source $root/scripts/add_capture.tcl
set identity_file [open $root/reports/v156/bd_model_id.txt w]
puts $identity_file [get_property CONFIG.MODEL_ID [get_bd_cells regions_regs]]
close $identity_file
validate_bd_design''',1);p.write_text(s)
paths=[p for folder in ['rtl','constraints','scripts','ip_repo'] for p in (B/folder).rglob('*') if p.is_file()]
(B/'reports/v156/SOURCE_INPUTS.json').write_text(json.dumps({p.relative_to(B).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
print(B)
