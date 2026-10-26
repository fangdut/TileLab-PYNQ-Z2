"""Download pinned upstream sources/checkpoint, verify Git blobs; do not execute."""
from pathlib import Path
import argparse,json,urllib.request,hashlib
PLAN = {'repo': 'https://github.com/RobotvisionLab/HFENet', 'commit': '6edf57293da051a5d9d2164482f88b68ef45c11f', 'files': [{'path': 'hfenet.py', 'sha': '9c92cc5cf1a337a762a7658df19acc4e27ed2bcd', 'bytes': 6100}, {'path': 'main.py', 'sha': '81ea4e0223534e1ea4998f9b39e059fc148f3235', 'bytes': 8833}, {'path': 'utils.py', 'sha': 'a2948056b81b9dcd83c25a4709da036a961c6810', 'bytes': 1791}, {'path': 'LICENSE', 'sha': 'e4ff17a3d6744c3d42d718d0fe6abec32714d0e9', 'bytes': 1071}, {'path': 'checkpoint/model_epoch_69.pth', 'sha': '5ee9e2931903e996761f51df9c68617e0931c319', 'bytes': 708579}], 'checkpoint_selection': 'Highest numbered published epoch69 chosen before any scores; no new training; evaluate original contract then fixed crop separately.', 'purpose': 'OFFLINE_REFERENCE_FEASIBILITY_NOT_CPU_DEPLOYMENT'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);records=[]
    for row in PLAN['files']:
        url='https://raw.githubusercontent.com/RobotvisionLab/HFENet/'+PLAN['commit']+'/'+row['path']
        raw=urllib.request.urlopen(url,timeout=60).read()
        if len(raw)!=row['bytes'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['sha']:raise ValueError('Upstream identity mismatch: '+row['path'])
        target=a.out/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);records.append(dict(row,sha256=hashlib.sha256(raw).hexdigest()))
    (a.out/'source.json').write_text(json.dumps(dict(plan=PLAN,verified=records),indent=2),encoding='utf8')
    print('Verified sources saved; import hfenet.py only, never main.py (CUDA/training initialization).')
if __name__=='__main__':main()
