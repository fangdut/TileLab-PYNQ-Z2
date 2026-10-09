from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1]
for old,new in [('board_v15_continuous.py','board_v16_continuous.py'),('audit_v15_motion.py','audit_v16_motion.py')]:
 s=(R/'scripts'/old).read_text(encoding='utf-8-sig').replace("from valley_reference import detect","from weak_reference import detect").replace('reports/v15','reports/v132')
 if not (R/'scripts'/new).exists():(R/'scripts'/new).write_text(s,encoding='utf-8')
for p in (R/'data/real_tiles/hdmi').glob('real_*.png'):
 n=int(p.stem.split('_')[1]);im=Image.open(p).convert('RGB');draw=ImageDraw.Draw(im)
 for bit in range(16):draw.rectangle((1018+bit*14,22,1024+bit*14,37),fill='white' if ((0x6000+n)>>bit)&1 else 'black')
 draw.rectangle((0,665,1279,719),fill=im.getpixel((0,680)))
 draw.text((24,680),'Source: MVTec Software GmbH | CC BY-NC-SA 4.0 | Test stimulus only; detection parameters are selected on FPGA',fill=(190,210,215))
 im.save(p)
