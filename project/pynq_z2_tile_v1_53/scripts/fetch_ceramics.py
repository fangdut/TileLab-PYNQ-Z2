"""Download only the 1,600 original, unaugmented public photographs; verify SHA256."""
from pathlib import Path
import json,urllib.request,hashlib,concurrent.futures,time
R=Path(__file__).resolve().parents[1];D=R/'data/ceramics_mendeley'
meta=json.loads((D/'source_metadata.json').read_text());folders={f['id']:f for f in json.loads((D/'folders.json').read_text())}
def folder_path(key):
    f=folders[key];return (folder_path(f['parent_id'])+'/' if f.get('parent_id') else '')+f['name']
items=[]
for f in meta['files']:
    path=folder_path(f['folder_id'])+'/'+f['filename']
    if '/amostra/' not in path:continue
    items.append(dict(id=f['id'],source_path=path,image='originals/'+path.removeprefix('database/amostra/'),split='train' if '/Treino/' in path else 'test',label='normal' if '/normais/' in path else 'defective',sha256=f['content_details']['sha256_hash'],bytes=f['size'],url=f['content_details']['download_url']))
assert len(items)==1600
manifest=dict(dataset=meta['name'],doi=meta['doi']['id'],source='https://data.mendeley.com/datasets/47x6jdbr5j/1',license='CC BY 4.0',contributors=meta['contributors'],scope='REAL CERAMIC ROOF TILES, not flat floor tiles; limited physical samples, repeated views; cross-domain stress only, not independent factory accuracy',split_policy='Original author splits retained for traceability; physical-sample independence not established; no augmented images',samples=items)
(D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
def fetch(row):
    p=D/row['image'];p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']:return True
    for attempt in range(4):
        try:
            b=urllib.request.urlopen(urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read()
            assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],'hash mismatch'
            p.write_bytes(b);return True
        except Exception as e:
            if attempt==3:return dict(id=row['id'],error=str(e))
            time.sleep(attempt+1)
fail=[];start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(8) as pool:
    for i,r in enumerate(pool.map(fetch,items),1):
        if r is not True:fail.append(r)
        if i%50==0:print(json.dumps(dict(done=i,total=len(items),failed=len(fail),seconds=round(time.monotonic()-start))),flush=True)
result=dict(total=len(items),verified=len(items)-len(fail),failures=fail,bytes=sum(x['bytes'] for x in items),seconds=time.monotonic()-start)
(D/'download_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if fail:raise SystemExit(1)
