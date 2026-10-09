"""Deterministic test-only textures, not real product photos or detector output."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];out=R/'data/dark_gate';out.mkdir(exist_ok=True)
tiles=[]
for index in range(4):
    level=70 if index<2 else 110
    defect=index%2==1
    im=Image.new('RGB',(500,500),(level,)*3)
    if defect:
        # Equal intended contrast (55) at both surface levels. Actual HDMI RGB
        # is measured from the board; display color transforms are not assumed.
        ImageDraw.Draw(im).line([(120,25),(230,195),(195,305),(365,475)],fill=(level-55,)*3,width=5)
    path=out/f'tile_{index}.png';im.save(path)
    tiles.append(dict(index=index,level=level,crack_level=level-55 if defect else None,defect=defect,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
manifest=dict(kind='SYNTHETIC_CONTROLLED_FIXTURE_NOT_REAL_TILE',width=1280,height=720,tile_width=500,tile_height=500,background_rgb=[8]*3,speed_px_per_second=480,source_fps=60,source_period=720,tiles=tiles,
    x_formula='((source_frame*8-index*1440+500)%5760+5760)%5760-500',scope='Engineering presence-gate regression only; no industrial accuracy claim')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(tiles=len(tiles),bytes=sum(p.stat().st_size for p in out.iterdir() if p.is_file()))))
