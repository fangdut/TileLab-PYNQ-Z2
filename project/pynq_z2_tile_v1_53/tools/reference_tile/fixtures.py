"""Procedural engineering fixtures, NOT photographs or real cracked tiles."""
import io
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

STYLES=('floral','geometry','stripes','woodlike','grain','plain')

def frame(style='floral'):
    index=STYLES.index(style);rng=np.random.default_rng(16500+index);y,x=np.mgrid[:500,:500]
    if style=='woodlike':
        value=18*np.sin(x*.08+np.sin(y*.011)*2)+6*np.sin(x*.031+y*.009)
        rgb=np.stack([165+value,125+value*.8,85+value*.5],axis=-1)
    elif style=='grain':
        a=rng.integers(30,225,(500,500),dtype=np.uint8);gray=np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(.7))).astype(float)
        rgb=np.stack([gray*.8+30,gray*.7+40,gray*.65+35],axis=-1)
    elif style=='stripes':
        colors=np.array([[180,65,75],[65,150,180],[205,190,120],[85,100,160]],float);rgb=colors[(x//18+y//120)%4]
    else:
        rgb=np.broadcast_to(np.array([[190,180,150] if style!='plain' else [170,125,85]],float),(500,500,3)).copy()
        if style!='plain':rgb+=rng.normal(0,.25,(500,500,1))
    im=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8));d=ImageDraw.Draw(im)
    if style=='floral':
        for cy in range(55,500,135):
            for cx in range(50,500,140):
                d.line([(cx,cy),(cx-15,cy+50),(cx+20,cy+95)],fill=(45,115,70),width=6)
                for dx,dy in [(-13,0),(13,0),(0,-13),(0,13)]:d.ellipse([cx+dx-15,cy+dy-15,cx+dx+15,cy+dy+15],fill=(155,65+(cx%30),115))
                d.ellipse([cx-8,cy-8,cx+8,cy+8],fill=(220,175,45))
    if style=='geometry':
        colors=[(55,110,170),(180,65,80),(75,155,120),(210,165,60)]
        for cy in range(0,500,75):
            for cx in range(0,500,80):d.polygon([(cx,cy),(cx+65,cy+12),(cx+20,cy+65)],fill=colors[(cx//80+cy//75)%4])
    if style=='stripes':d.ellipse([31,40,81,90],fill=(180,120,55))
    a=np.full((720,1280,3),27,np.uint8);a[110:610,390:890]=np.array(im);return a

def add_defect(source,width=2,bright=False,edge=False):
    # Exact artificial line mask; every generated line pixel stays in GT,
    # including low-contrast crossings and all declared surface-edge pixels.
    im=Image.new('L',(500,500));d=ImageDraw.Draw(im)
    points=[(0,2),(70,36),(155,110),(260,210),(380,346),(499,496)] if edge else [(45,60),(130,120),(225,225),(350,360),(465,420)]
    d.line(points,fill=255,width=width);truth=np.array(im)>0;a=source.copy();tile=a[110:610,390:890].astype(np.int16)
    tile[truth]=np.clip(tile[truth]+(75 if bright else -75),0,255);a[110:610,390:890]=tile.astype(np.uint8);return a,truth

def capture(source,dx=0,dy=0,gains=(1,1,1),offsets=(0,0,0),noise=0,blur=0,angle=0,jpeg=None,seed=165):
    im=Image.fromarray(source)
    if angle:im=im.rotate(angle,resample=Image.Resampling.BILINEAR,center=(640,360),fillcolor=(27,27,27))
    if dx or dy:im=im.transform(im.size,Image.Transform.AFFINE,(1,0,-dx,0,1,-dy),Image.Resampling.BILINEAR,fillcolor=(27,27,27))
    if blur:im=im.filter(ImageFilter.GaussianBlur(blur))
    a=np.asarray(im).astype(np.float32)*np.array(gains)+np.array(offsets)
    if noise:a+=np.random.default_rng(seed).normal(0,noise,a.shape)
    a=np.clip(np.rint(a),0,255).astype(np.uint8)
    if jpeg:
        b=io.BytesIO();Image.fromarray(a).save(b,format='JPEG',quality=jpeg)
        with Image.open(io.BytesIO(b.getvalue())) as encoded:a=np.array(encoded.convert('RGB'))
    return a
