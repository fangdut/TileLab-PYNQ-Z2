"""Preload the same four real photographs used by the MP4 source timeline."""
from pathlib import Path
import json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'data/real_tiles';out=D/'motion';out.mkdir(exist_ok=True)
items=json.loads((D/'video_manifest.json').read_text())['items'];rows=[]
for n,item in enumerate(items):
 p=out/f'tile_{n}.png'
 Image.open(D/item['image']).convert('RGB').resize((500,500),Image.Resampling.BILINEAR).save(p)
 rows.append(dict(id=item['id'],image=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(out/'manifest.json').write_text(json.dumps(dict(source='MVTec AD',license='CC BY-NC-SA 4.0',purpose='Preloaded HDMI rendering, no host detection',items=rows),indent=2))
print('Prepared four source textures; source timing matches existing video_manifest.json')
