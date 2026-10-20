"""OFFLINE: reconstruct the sealed FPGA blob from a small frozen profile.

This avoids committing a duplicate 100 MB pretrained network to GitHub.
The actual workstation never imports or invokes this script.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,urllib.request
URL='https://download.pytorch.org/models/wide_resnet50_2-95faca4d.pth'
WEIGHTS_SHA='95faca4d11227dddf8633dbb5ff6c8a9003c1aa5b8945c73834b8007b10950b8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--weights-cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Use a new output directory')
    record=json.loads((a.profile/'model.json').read_text());graph=json.loads((a.profile/'graph.json').read_text())
    if sha(a.profile/'compression.npz')!=record['compression_sha256'] or record['pretrained_sha256']!=WEIGHTS_SHA:raise ValueError('Profile/checkpoint identity mismatch')
    weights=a.weights_cache
    if not weights.exists():
        weights.parent.mkdir(parents=True,exist_ok=True);part=weights.with_suffix(weights.suffix+'.download')
        if part.exists():raise ValueError('Existing partial checkpoint; preserve or inspect it first')
        with urllib.request.urlopen(URL,timeout=60) as response,part.open('xb') as f:shutil.copyfileobj(response,f)
        if sha(part)!=WEIGHTS_SHA:raise ValueError('Downloaded checkpoint SHA failed')
        part.rename(weights)
    if sha(weights)!=WEIGHTS_SHA:raise ValueError('Cached checkpoint SHA failed')
    a.out.mkdir(parents=True)
    for name in ('model.json','compression.npz','summary.json','results.json','fit_protocol.json','normal_calibration.json'):
        shutil.copy2(a.profile/name,a.out/name)
    for path in a.profile.glob('*_scores.npy'):shutil.copy2(path,a.out/path.name)
    subprocess.run([sys.executable,str(Path(__file__).with_name('export_graph.py')),'--weights',str(weights),'--model',str(a.out)],check=True)
    if sha(a.out/'model.bin')!=graph['sha256']:raise RuntimeError('Reconstructed weights differ; use the pinned CPU Torch version from the profile environment')
    print('Exact FPGA model SHA verified: '+graph['sha256'],flush=True)
if __name__=='__main__':main()
