from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
p=Path(__file__).resolve().parent.parent/'test_patterns'
p.mkdir(exist_ok=True)
im=Image.new('RGB',(1280,720),'black');d=ImageDraw.Draw(im)
# Unscaled 8-bit RGB levels, geometry/weak edges/diagonals and ramps.
d.rectangle((80,80,300,300),fill=(255,255,255));d.rectangle((380,80,600,300),fill=(255,0,0))
d.rectangle((680,80,900,300),fill=(0,255,0));d.rectangle((980,80,1200,300),fill=(0,0,255))
d.ellipse((80,370,300,590),fill=(80,80,80));d.polygon([(390,590),(500,370),(610,590)],fill=(160,160,160))
for x in range(680,920):d.line((x,370,x,590),fill=((x-680),)*3)
for x in range(980,1200,20):d.rectangle((x,370,x+9,590),fill=(255,255,255))
for x in range(1280):d.line((x,650,x,719),fill=((x*255//1279),)*3)
im.save(p/'geometry_720p.bmp')
def golden(arr):
 a=arr.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
 gx=gray[:-2,2:]+2*gray[1:-1,2:]+gray[2:,2:]-gray[:-2,:-2]-2*gray[1:-1,:-2]-gray[2:,:-2]
 gy=gray[2:,:-2]+2*gray[2:,1:-1]+gray[2:,2:]-gray[:-2,:-2]-2*gray[:-2,1:-1]-gray[:-2,2:]
 mag=np.zeros(gray.shape,dtype=np.uint16);mag[1:-1,1:-1]=np.abs(gx)+np.abs(gy)
 edge=np.minimum(mag,255).astype(np.uint8)
 return gray.astype(np.uint8),mag,edge
for name,arr in [('geometry',np.asarray(im)),('sim_epoch0',None)]:
 if arr is None:
  yy,xx=np.indices((720,1280));arr=np.stack([(xx*3+yy*7+(xx//16)*51)%256,(xx*11+yy*5+(yy//9)*79)%256,(xx*7+yy*13)%256],axis=-1).astype(np.uint8)
  Image.fromarray(arr).save(p/'sim_epoch0_720p.bmp')
 gray,mag,edge=golden(arr)
 Image.fromarray(gray).save(p/f'{name}_gray_expected.bmp');Image.fromarray(edge).save(p/f'{name}_sobel_expected.bmp')
 np.save(p/f'{name}_magnitude_expected.npy',mag)
# Compact illustrative preview for reports; it is a software golden model.
pre=Image.new('RGB',(1280,280),'white')
for j,fn in enumerate(['geometry_720p.bmp','geometry_gray_expected.bmp','geometry_sobel_expected.bmp']):
 tile=Image.open(p/fn).convert('RGB').resize((416,234));pre.paste(tile,(j*432,30))
d=ImageDraw.Draw(pre);d.text((8,8),'INPUT RGB',fill='black');d.text((440,8),'EXPECTED GRAY',fill='black');d.text((872,8),'EXPECTED SOBEL (software)',fill='black')
pre.save(p/'golden_comparison.png')
(p/'README.md').write_text('''# V0.4 test patterns and golden model
All expected images are calculated offline; none is a measured FPGA screenshot.
geometry_720p.bmp: show at 1:1 on a true 1280x720 RGB8 60Hz HDMI output.
geometry_gray_expected.bmp and geometry_sobel_expected.bmp: compare shape/position/border behavior.
Exact pixels require unchanged RGB code values, no scaling/range conversion; monitor photos are qualitative.
Sobel uses centered 3x3, abs(Gx)+abs(Gy), saturation at 255, and ZERO outermost border.
*_magnitude_expected.npy retains the unsaturated unsigned integer magnitude.
sim_epoch0 files use the same analytic input pattern as the RTL test but an independent NumPy array implementation.
Reproduce by running scripts/golden_model.py with Python + NumPy + Pillow.
''',encoding='utf8')
print('Generated RGB/gray/Sobel test patterns and unsaturated magnitude arrays')
