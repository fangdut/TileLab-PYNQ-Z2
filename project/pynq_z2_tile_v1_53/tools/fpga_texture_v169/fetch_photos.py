"""Fetch original real photos by the frozen URLs and per-file SHA256 values."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,io,json,urllib.parse,urllib.request
from PIL import Image
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--examples-only',action='store_true');a=p.parse_args()
    if a.out.exists():raise ValueError('Use a new output folder')
    raw=a.manifest.read_bytes();manifest=json.loads(raw);items=manifest['images']
    if a.examples_only:items=[next(v for v in items if v['role']=='test' and v['label']==label) for label in ('good','crack')]
    a.out.mkdir(parents=True);files=[]
    for item in items:
        files.append(item)
        if item.get('mask'):files.append(item['mask'])
    def fetch(record):
        relative=Path(record['file'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid photo path')
        url=urllib.parse.urlsplit(record['url'])
        if url.scheme!='https' or url.hostname!='huggingface.co' or '/'+manifest['mirror_revision']+'/' not in url.path:raise ValueError('Unexpected source/revision')
        with urllib.request.urlopen(urllib.request.Request(record['url'],headers={'User-Agent':'TileLab-FPGA-V169'}),timeout=60) as response:data=response.read(24000001)
        if len(data)>24000000 or hashlib.sha256(data).hexdigest()!=record['sha256']:raise RuntimeError('Photo SHA failed: '+record['file'])
        with Image.open(io.BytesIO(data)) as im:
            if list(im.size)!=record['dimensions']:raise RuntimeError('Photo dimensions changed')
            im.verify()
        path=a.out/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return record['file']
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index,name in enumerate(pool.map(fetch,files),1):print(f'Original photo/mask verified {index}/{len(files)}: {name}',flush=True)
    manifest['images']=items;manifest['package_scope']='Two original test examples' if a.examples_only else 'Full frozen 347-photo dataset'
    manifest['original_manifest_sha256']=hashlib.sha256(raw).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
