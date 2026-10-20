"""Write or verify the repository snapshot; excludes the manifest itself."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--write',action='store_true');group.add_argument('--verify',action='store_true');a=ap.parse_args();target=ROOT/'PACKAGE_MANIFEST.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if a.write:
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0');names=sorted(n for n in names if n and n!='PACKAGE_MANIFEST.json')
    reference=(ROOT/'project/pynq_z2_tile_v1_53/config/reference_v165.json').exists()
    reference166=(ROOT/'project/pynq_z2_tile_v1_53/tools/reference_tile/reference_v166.py').exists()
    m=dict(version='V1.65-reference-prototype' if reference else 'V1.64',status='OFFLINE_REFERENCE_AND_EXPERIMENTAL_RTL' if reference else 'ENGINEERING_CANDIDATE',deployed_hardware_version='V1.64',requested_scope='Single painted/multiple-material tile',accuracy_qualified=False,board_accepted=False,base_commit='d8a96b1b91ae50c53b8440a6a62c026feb58bcf6',reference_base_commit='aa046369f468729d6a3bdf7272550223a6fa1cdf' if reference else None,files=len(names),uncompressed_bytes=sum((ROOT/n).stat().st_size for n in names),sha256={n:sha(ROOT/n) for n in names})
    if reference166:m.update(version='V1.66-reference-prototype',status='OFFLINE_REFERENCE_WITH_SEPARATE_BOARD_ARITHMETIC_AND_V164_TRANSPORT_PROOF',deployed_hardware_version='V1.64 classifier with independent V166 headless HPD ECO; separate V166 arithmetic BIST',reference_base_commit='a5afaeb57c367b9c3313d0e4a015ff1874d3926a')
    if (ROOT/'project/pynq_z2_tile_v1_53/releases/v167_r2/DEPLOYMENT.json').exists():m.update(version='V1.67.2-reference-prototype',status='FULL_FRAME_PL_REFERENCE_PIPELINE_ENGINEERING_PASSED_PHYSICAL_ACCURACY_UNQUALIFIED',deployed_hardware_version='V1.67 full-frame Q8 normalization and reference score; host registration/components',reference_base_commit='d67606f6e5332d3b443ad715a085f93b19f0445f')
    target.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
m=json.loads(target.read_text(encoding='utf8'))
if len(m['sha256'])!=m['files']:raise ValueError('Manifest count mismatch')
for name,digest in m['sha256'].items():
    p=(ROOT/name).resolve()
    if not p.is_relative_to(ROOT) or sha(p)!=digest:raise ValueError('Snapshot mismatch: '+name)
print(json.dumps(dict(version=m['version'],verified_files=m['files'],manifest_sha256=sha(target),accuracy_qualified=False)))
