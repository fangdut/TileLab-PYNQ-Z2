"""Acquire a NEW fixed-parameter cross-material holdout; never tune on results.

RGB images and labels only. Source is MCS2, CC BY 4.0. This dataset contains
cracked marble slabs, not normal ceramic products, so no image FPR is inferred.
"""
from pathlib import Path
import datetime
import hashlib
import io
import json
import urllib.request
import zipfile
from PIL import Image, ImageDraw

R=Path(__file__).resolve().parents[1]
D=R/'data/independent_mcs2'
URL='https://codeload.github.com/MachineLearningVisionRG/mcs2-dataset/zip/refs/heads/main'


def main():
    if (D/'manifest.json').exists():
        raise RuntimeError('Never replace a frozen holdout manifest')
    request=urllib.request.Request(URL,headers={'User-Agent':'TileLab-research/1.0'})
    with urllib.request.urlopen(request,timeout=90) as response:
        raw=response.read(128*1024*1024+1)
    assert len(raw)<=128*1024*1024,'Unexpected archive size'
    z=zipfile.ZipFile(io.BytesIO(raw))
    paths=sorted(n for n in z.namelist() if '/dataset/RGB/images/' in n and n.endswith('.png'))
    assert len(paths)==24,paths
    D.mkdir(parents=True,exist_ok=True)
    for folder in ('images','masks','hdmi','truth'): (D/folder).mkdir(exist_ok=True)
    rows=[]
    for index,name in enumerate(paths):
        stem=Path(name).stem;label=name.replace('/images/','/masks/')
        original,mask=z.read(name),z.read(label)
        (D/'images'/f'{stem}.png').write_bytes(original)
        (D/'masks'/f'{stem}.png').write_bytes(mask)
        with Image.open(io.BytesIO(original)) as photo:
            size=photo.size;texture=photo.convert('RGB').resize((500,500),Image.Resampling.LANCZOS)
        with Image.open(io.BytesIO(mask)) as source:
            assert source.size==size
            truth=source.convert('L').resize((500,500),Image.Resampling.NEAREST)
        scene=Image.new('RGB',(1280,720),(30,39,44));scene.paste(texture,(390,110))
        draw=ImageDraw.Draw(scene)
        for bit in range(16):
            draw.rectangle((1016+bit*14,20,1027+bit*14,39),fill='white' if (0x7000+index)&(1<<bit) else 'black')
        scene.save(D/'hdmi'/f'holdout_{index:03d}.png')
        gt=Image.new('L',(1280,720),0);gt.paste(truth,(390,110));gt.save(D/'truth'/f'holdout_{index:03d}.png')
        rows.append(dict(index=index,source_name=stem,original_size=list(size),label='crack',
                         image_sha256=hashlib.sha256(original).hexdigest(),mask_sha256=hashlib.sha256(mask).hexdigest(),
                         scene_sha256=hashlib.sha256((D/'hdmi'/f'holdout_{index:03d}.png').read_bytes()).hexdigest()))
    license_name=next(n for n in z.namelist() if n.endswith('/LICENSE'))
    (D/'LICENSE.txt').write_bytes(z.read(license_name))
    result=dict(dataset='MCS2 RGB',source='https://github.com/MachineLearningVisionRG/mcs2-dataset',
                license='CC BY 4.0',attribution='Vrochidou et al., Fusion of Thermal and RGB Images for Automated Deep Learning Based Marble Crack Detection, AIIoT 2023, DOI 10.1109/AIIoT58121.2023.10174288',
                downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive_sha256=hashlib.sha256(raw).hexdigest(),
                fixed_before_inspection=dict(high=90,low=45,passes=4,minimum_support=3,seed_radius=8,weak_radii=[8,16]),
                independence='New to this project; no threshold selection on these 24 images. Cross-material holdout, not factory validation.',
                limitations='24 cracked marble images only; no normal-image false alarm rate; resize changes physical scale; physical sample identity unavailable.',items=rows)
    (D/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(images=len(rows),archive_bytes=len(raw),manifest=str(D/'manifest.json'))))


if __name__=='__main__':main()
