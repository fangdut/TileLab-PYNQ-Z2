"""Offline V159 arithmetic reference with the V164 full single-tile ROI.

Never imported by the live workstation or ARM firmware. No fitting/training.
Input must already be aligned; no inferred tile boundary or hidden border crop.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models'))
sys.path.insert(0,str(ROOT/'host'))
from single_tile_profile import load
from valley_reference import valley
from directional_link_reference import direction_planes,shoulder_noise
from tree_features_v155 import feature_matrix
from weak_reference import grow
from ridge_reference import shifted
from region_quality_reference_v157 import quality_regions
from fine_integer_reference import predict,validate

def features(rgb):
    a=np.asarray(rgb,dtype=np.int32)
    if a.shape!=(720,1280,3):raise ValueError('Expected aligned RGB1280x720')
    gray=(77*a[...,0]+150*a[...,1]+29*a[...,2])>>8
    n=valley(gray,8);w=valley(gray,16);s=direction_planes(gray,8);l=direction_planes(gray,16)
    x=feature_matrix(gray,n,w,s,l,direction_planes(gray,8,4),direction_planes(gray,16,8),shoulder_noise(gray))
    color=np.stack([(a[...,0]-a[...,1]+256)>>1,(a[...,1]-a[...,2]+256)>>1],axis=-1).astype(np.uint8)
    return np.concatenate([x,color],axis=-1),n,w,s.max(axis=0),l.max(axis=0)

def infer(rgb,model,backend=None):
    p=load(ROOT);validate(model);x,n,w,s,l=features(rgb)
    keep=np.zeros((720,1280),bool);x0,y0,x1,y1=p['inspection_roi'];keep[y0:y1+1,x0:x1+1]=True
    score=np.full(keep.shape,-1073741824,np.int32)
    score[keep]=backend.predict(x[keep]) if backend else predict(x[keep],model)
    base=((n>90)|(s>40)|(l>48))&keep;weak=((n>45)|(w>45)|(s>20)|(l>24))&keep
    for _ in range(4):
        base=grow(base,weak,3);base[[0,-1]]=False;base[:,[0,-1]]=False
    raw=(score>=p['high_q16'])&keep
    support=sum(shifted(raw.astype(np.uint8),dx,dy) for dy in (-1,0,1) for dx in (-1,0,1))
    trusted=raw&(support>=p['support'])
    mask=((base&(score>=p['gate_q16']))|trusted)&keep
    regions=quality_regions(mask,trusted)
    return mask,dict(profile_id=p['profile_id'],profile_sha256=p['profile_sha256'],roi=p['inspection_roi'],
        candidate_pixels=int(mask.sum()),regions=regions,alarm=bool(regions['boxes'] or regions['overflow']),
        scope='OFFLINE_SOFTWARE_REFERENCE_NOT_A_BOARD_TEST',accuracy_qualified=False)

def read_input(path,fit=False):
    with Image.open(path) as im:
        im=im.convert('RGB')
        if fit:
            if im.width!=im.height:raise ValueError('Fit mode requires a square single-tile crop, without wall/grout/background')
            tile=im.resize((500,500),Image.Resampling.BILINEAR);frame=Image.new('RGB',(1280,720));frame.paste(tile,(390,110));return np.array(frame)
        if im.size!=(1280,720):raise ValueError('Use aligned720p input or explicitly pass --fit-single-tile for a square tile crop')
        return np.array(im)

def save_result(out,rgb,mask,result):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    Image.fromarray(rgb).save(out/'input.png');Image.fromarray(mask.astype(np.uint8)*255).save(out/'mask.png')
    overlay=rgb.copy();overlay[mask]=(overlay[mask]//2+np.array([127,0,0],np.uint8));im=Image.fromarray(overlay);draw=ImageDraw.Draw(im)
    for box in result['regions']['boxes']:draw.rectangle(box,outline='red',width=2)
    draw.rectangle(result['roi'],outline='cyan',width=1);im.save(out/'overlay.png')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('image',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--fit-single-tile',action='store_true');ap.add_argument('--native-library',type=Path);args=ap.parse_args()
    p=load(ROOT);model_path=ROOT/'models/v159_integer_model.json';model=json.loads(model_path.read_text());backend=None
    if args.native_library:
        from fine_integer_native import NativeBoost
        backend=NativeBoost(model,args.native_library)
    started=time.perf_counter();rgb=read_input(args.image,args.fit_single_tile);mask,result=infer(rgb,model,backend)
    result.update(input_sha256=hashlib.sha256(args.image.read_bytes()).hexdigest(),model_sha256=p['model_sha256'],seconds=time.perf_counter()-started,explicit_square_resize=args.fit_single_tile,decision='crack_candidate' if result['alarm'] else 'no_crack_candidate_in_declared_roi')
    save_result(args.out,rgb,mask,result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
