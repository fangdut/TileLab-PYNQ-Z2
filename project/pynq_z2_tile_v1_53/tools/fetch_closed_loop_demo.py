"""Recreate frozen public demo inputs offline, never a runtime image fallback."""
from pathlib import Path
import argparse,json,hashlib,urllib.request,io
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--expected',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=json.loads(a.catalog.read_text(encoding='utf8'));sources={r['id']:r for r in json.loads(a.source_manifest.read_text())['images']}
    a.out.mkdir(parents=True,exist_ok=False)
    def fetch(row):
        request=urllib.request.Request(row['source_url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=90) as response:raw=response.read()
        target=(a.out/row['file']).resolve()
        if not target.is_relative_to(a.out.resolve()):raise ValueError('Invalid input path')
        target.parent.mkdir(parents=True,exist_ok=True)
        if row.get('preparation'):
            source=sources[row['id'].removeprefix('roof_')]
            if sha(raw)!=source['original_sha256']:raise ValueError('Author original hash differs')
            with Image.open(io.BytesIO(raw)) as im:im.convert('RGB').resize((720,720),Image.Resampling.BILINEAR).save(target)
            if sha(target.read_bytes())!=row['sha256']:raise ValueError('PNG encoder differs from frozen inputs; use packaged photos or the recorded preparation environment')
        else:
            if sha(raw)!=row['sha256']:raise ValueError('Public original hash differs')
            target.write_bytes(raw)
        return row['id']
    done=list(ThreadPoolExecutor(max_workers=4).map(fetch,rows))
    (a.out/'catalog.json').write_bytes(a.catalog.read_bytes());(a.out/'expected_offline_only.json').write_bytes(a.expected.read_bytes())
    print(json.dumps(dict(verified_photos=len(done),scope='OFFLINE_DEMO_RECREATION_NOT_RUNTIME_DETECTION')))
if __name__=='__main__':main()
