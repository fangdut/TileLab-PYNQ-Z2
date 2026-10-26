"""Recreate the frozen public reference-calibration pilot, not a live detector.

Downloads author originals with published SHA256 verification, then recreates
the explicitly disclosed offline 720-square bilinear derivatives.
"""
from pathlib import Path
import argparse, hashlib, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parents[1]/'reports/v195/r2/source')
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    plan=(a.evidence/'plan.json').read_bytes(); manifest=(a.evidence/'manifest.json').read_bytes()
    expected=json.loads(manifest)
    assert hashlib.sha256(plan).hexdigest()==expected['plan_sha256']
    (a.out/'plan.json').write_bytes(plan); (a.out/'manifest.json').write_bytes(manifest)
    (a.out/'originals').mkdir(); (a.out/'prepared').mkdir()
    def fetch(row):
        req=urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=90) as response:raw=response.read()
        if hashlib.sha256(raw).hexdigest()!=row['original_sha256'] or len(raw)!=row['bytes']:
            raise ValueError('Original integrity failed: '+row['id'])
        original=a.out/row['original']; original.write_bytes(raw)
        with Image.open(original) as im:
            im.convert('RGB').resize((720,720),Image.Resampling.BILINEAR).save(a.out/row['file'])
        # PNG container hashes may depend on Pillow/zlib; reject rather than
        # silently claim exact frozen-input reproduction with another encoder.
        if hashlib.sha256((a.out/row['file']).read_bytes()).hexdigest()!=row['prepared_sha256']:
            raise ValueError('Prepared PNG differs; use the recorded Pillow version before evaluating')
        return row['id']
    done=list(ThreadPoolExecutor(max_workers=5).map(fetch,expected['images']))
    print(json.dumps(dict(verified_images=len(done),scope='OFFLINE_REFERENCE_PILOT_INPUT_RECREATION')))

if __name__=='__main__':main()
