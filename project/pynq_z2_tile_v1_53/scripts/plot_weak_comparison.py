"""Diagnostic figure: actual captured pixels and computed masks, no AI retouching."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5';sys.path.insert(0,str(R/'models'))
from valley_reference import detect as baseline
from weak_reference import detect
from regions_reference import regions
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
fig=Image.new('RGB',(1564,1250),'#f4f7f8');draw=ImageDraw.Draw(fig)
draw.text((28,18),'弱裂纹响应补全：红色为候选像素，矩形为候选区域',font=font,fill='#133e46')
for row,n in enumerate((5,0)):
 p=R/f'reports/v132/real_board/real_{n:03d}_original.png'
 live=p.exists()
 if not live:p=B/f'reports/v15/real_board/real_{n:03d}_original.png'
 im=Image.open(p).convert('RGB');a=np.asarray(im);old,_=baseline(im,threshold=89);new,_=detect(im,threshold=89)
 if live:
  actual=np.asarray(Image.open(R/f'reports/v132/real_board/real_{n:03d}_mask.png'))>0
  assert np.array_equal(actual,new)
 for col,(title,mask) in enumerate([('实采原图',None),('V1.5 单阈值',old),('V1.6 双阈值 + 邻域支持',new)]):
  panel=Image.fromarray(a[110:610,390:890].copy());overlay=ImageDraw.Draw(panel)
  if mask is not None:
   m=mask[110:610,390:890];pix=np.asarray(panel).copy();pix[m]=[255,24,54];panel=Image.fromarray(pix);overlay=ImageDraw.Draw(panel)
   rr=regions(mask)
   for x0,y0,x1,y1 in rr['boxes']:overlay.rectangle((x0-390,y0-110,x1-390,y1-110),outline='#ff244c',width=2)
   title+=f"\n{'报警' if rr['boxes'] else '未报警'} · {int(mask.sum())} 候选像素"
  left=20+col*518;top=60+row*565;draw.text((left,top),title,font=small,fill='#133e46');fig.paste(panel,(left,top+52))
draw.text((25,1192),('V1.6 掩码已逐像素匹配实板；V1.5 列为同一实采 RGB 的旧规则对照。' if live else '历史实采图上的离线对照；尚不代表本版实板输出。')+'\n样本来自 MVTec AD tile；历史回归用于开发，不是工厂盲测。',font=small,fill='#476772')
fig.save(R/'reports/weak_crack/comparison.png')
print('Comparison figure generated; current board evidence:',live)
