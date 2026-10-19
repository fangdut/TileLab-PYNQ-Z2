"""Write or verify the repository snapshot; excludes the manifest itself."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--write',action='store_true');group.add_argument('--verify',action='store_true');a=ap.parse_args();target=ROOT/'PACKAGE_MANIFEST.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if a.write:
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0');names=sorted(n for n in names if n and n!='PACKAGE_MANIFEST.json')
    m=dict(version='V1.64',status='ENGINEERING_CANDIDATE',requested_scope='Single painted/multiple-material tile',accuracy_qualified=False,board_accepted=False,base_commit='d8a96b1b91ae50c53b8440a6a62c026feb58bcf6',files=len(names),uncompressed_bytes=sum((ROOT/n).stat().st_size for n in names),sha256={n:sha(ROOT/n) for n in names})
    target.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
m=json.loads(target.read_text(encoding='utf8'))
if len(m['sha256'])!=m['files']:raise ValueError('Manifest count mismatch')
for name,digest in m['sha256'].items():
    p=(ROOT/name).resolve()
    if not p.is_relative_to(ROOT) or sha(p)!=digest:raise ValueError('Snapshot mismatch: '+name)
print(json.dumps(dict(version=m['version'],verified_files=m['files'],manifest_sha256=sha(target),accuracy_qualified=False)))
