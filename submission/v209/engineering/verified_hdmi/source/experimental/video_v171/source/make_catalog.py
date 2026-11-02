"""Prepare original-photo HDMI playback input; no detection or image editing."""
from pathlib import Path
import argparse,hashlib,json


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--all-test',action='store_true')
    a=p.parse_args();dataset=a.dataset.resolve()
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf8'))
    ids=['6621d769324f6e05d5838381','6621d769324f6e05d583835f']
    rows=[r for r in manifest['images'] if r['role']=='test']
    if not a.all_test:rows=[next(r for r in rows if r['id']==i) for i in ids]
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate input photo')
    catalog=[]
    for r in rows:
        image=(dataset/r['file']).resolve()
        if not image.is_relative_to(dataset):raise ValueError('Photo escapes dataset directory')
        if hashlib.sha256(image.read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('Original photo provenance mismatch: '+r['id'])
        catalog.append(dict(id=r['id'],file=str(image),sha256=r['sha256'],label=r['label'],
            source_url=r['url'],original_unedited=True,benchmark_is_blind=False))
    with a.out.open('x',encoding='utf8') as f:json.dump(catalog,f,ensure_ascii=False,indent=2)
    print(json.dumps(dict(scope='PLAYBACK_INPUT_ONLY_NO_DETECTION',photos=len(catalog),out=str(a.out))))


if __name__=='__main__':main()
