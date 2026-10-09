"""Offline bit-accurate reference for this project's integer image algorithm.

Input is RGB PNG, output is a mask/overlay plus optional ground-truth metrics.
This is an OFFLINE software result, not a capture from the new FPGA build.
"""
from pathlib import Path
import argparse,json,zlib
import numpy as np
from PIL import Image
from vision_control import Profile

def conv(a,k):
    h,w=a.shape;out=np.zeros((h,w),np.int32)
    for j in range(3):
        for i in range(3):out[1:-1,1:-1]+=a[j:j+h-2,i:i+w-2]*k[j][i]
    return out
def morph(a,dilate):
    s=conv(a.astype(np.int32),[[1]*3]*3)
    out=s>0 if dilate else s==9
    out[[0,-1],:]=False;out[:,[0,-1]]=False
    return out
def detect(rgb,profile):
    profile.validate();rgb=np.asarray(rgb)
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8 or min(rgb.shape[:2])<3:
        raise ValueError('uint8 RGB image at least 3x3 required')
    h,w=rgb.shape[:2];v=rgb.astype(np.int32)
    gray=(77*v[:,:,0]+150*v[:,:,1]+29*v[:,:,2])>>8
    yy,xx=np.indices((h,w));roi=np.ones((h,w),bool)
    if profile.roi:
        x0,y0,x1,y1=profile.roi
        if x1>=w or y1>=h:raise ValueError('ROI exceeds actual image')
        roi=(xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1)
    mean=int(gray[roi].sum())//int(roi.sum())
    threshold=max(16,min(240,mean+(-profile.margin if profile.dark else profile.margin))) if profile.automatic else profile.threshold
    intensity=gray
    if profile.source==1:intensity=conv(gray,[[1,2,1],[2,4,2],[1,2,1]])//16
    if profile.source==2:
        intensity=np.minimum(abs(conv(gray,[[-1,0,1],[-2,0,2],[-1,0,1]]))+abs(conv(gray,[[-1,-2,-1],[0,0,0],[1,2,1]])),255)
    raw=((intensity<threshold) if profile.dark else (intensity>threshold))&roi
    mask=morph(morph(raw,bool(profile.closing)),not bool(profile.closing))&roi
    y,x=np.where(mask);box=[int(x.min()),int(y.min()),int(x.max()),int(y.max())] if x.size else None
    info={'mode':'OFFLINE_REFERENCE','count':int(mask.sum()),'bbox':box,'mean':mean,'threshold':threshold,
          'crc':f'{zlib.crc32(np.packbits(mask.ravel(),bitorder="little").tobytes()):08X}',
          'automatic_note':'converged target only; ignores hardware temporal slew and deadband'}
    return mask,info
def metrics(pred,truth):
    pred=np.asarray(pred,dtype=bool);truth=np.asarray(truth,dtype=bool)
    if pred.shape!=truth.shape:raise ValueError('ground truth dimensions differ')
    tp=int((pred&truth).sum());fp=int((pred&~truth).sum());fn=int((~pred&truth).sum())
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,iou=tp/(tp+fp+fn) if tp+fp+fn else None)
def save_outputs(rgb,mask,info,out,box=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    overlay=np.asarray(rgb).copy();overlay[mask]=[255,0,0]
    if box and info['bbox']:
        a,b,c,d=info['bbox'];overlay[b,a:c+1]=[255,255,0];overlay[d,a:c+1]=[255,255,0]
        overlay[b:d+1,a]=[255,255,0];overlay[b:d+1,c]=[255,255,0]
    Image.fromarray(mask.astype(np.uint8)*255).save(out/'mask.png')
    Image.fromarray(overlay).save(out/'overlay_OFFLINE.png')
    (out/'result.json').write_text(json.dumps(info,indent=2),encoding='utf8')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('image',type=Path);ap.add_argument('--profile',type=Path,required=True)
    ap.add_argument('--truth',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    rgb=np.array(Image.open(args.image).convert('RGB'));profile=Profile.load(args.profile);mask,info=detect(rgb,profile)
    if args.truth:info['metrics']=metrics(mask,np.array(Image.open(args.truth).convert('L'))>127)
    save_outputs(rgb,mask,info,args.out,bool(profile.box));print(json.dumps(info,indent=2))
if __name__=='__main__':main()
