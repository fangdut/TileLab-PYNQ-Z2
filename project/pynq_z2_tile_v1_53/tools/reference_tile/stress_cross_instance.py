"""Real normal-to-normal cross-instance stress, not verified same-pattern pairs."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image
from reference_tile import ROOT,compare,policy,canonical,sha
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
algorithm_path=Path(__file__).with_name('reference_tile.py');algorithm_sha=sha(algorithm_path);p=policy()
data=ROOT/'data/real_tiles';items=[r for r in json.loads((data/'hdmi_manifest.json').read_text())['items'] if r['label']=='good'];reference=items[0]
with Image.open(data/reference['image']) as im:ref=np.array(im.convert('RGB'))
rows=[]
for item in items[1:]:
    with Image.open(data/item['image']) as im:current=np.array(im.convert('RGB'))
    result,_,_=compare(ref,current,p);row=dict(id=item['id'],index=item['index'],source_sha256=sha(data/item['image']),source_label='good',same_pattern_or_pose_verified=False,**result);rows.append(row)
    print(json.dumps(dict(index=item['index'],status=result['status'],alarm=result['alarm'],reason=result.get('reason'))),flush=True)
if sha(algorithm_path)!=algorithm_sha or p!=policy():raise RuntimeError('Source/policy changed during stress run')
report=dict(scope='REAL_UNMODIFIED_NORMAL_PHOTOS_CROSS_INSTANCE_STRESS_NOT_VERIFIED_SAME_PATTERN_OR_POSE',accuracy_qualified=False,reference_id=reference['id'],reference_sha256=sha(data/reference['image']),policy_sha256=hashlib.sha256(canonical(p)).hexdigest(),algorithm_sha256=algorithm_sha,cases=len(rows),compared=sum(r['status']=='COMPARED' for r in rows),rejected=sum(r['status']=='REJECTED_INPUT' for r in rows),candidate_alarms=sum(r['alarm'] is True for r in rows),no_candidate=sum(r['alarm'] is False for r in rows),interpretation='A single per-category photo is not automatically a spatially matching per-pattern template; reject rate must not be hidden as zero false alarms',rows=rows)
(a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
