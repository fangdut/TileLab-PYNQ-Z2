"""Offline V166: full-resolution luma, 3x3 mean chroma, no classifier training.

Frozen V165 registration/photometry remain the implementation dependencies.
This is an experimental comparison metric, not the deployed FPGA detector.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from PIL import Image
import reference_tile as base

ROOT=base.ROOT

def policy():
    p=base.policy().copy()
    p.update(version='V1.66-reference-prototype',metric='YCOCG_LUMA_NATIVE_MEAN3_AND_REFERENCE_SPAN5_CHROMA',chroma_radius=1,reference_chroma_span_radius=2,edge_tolerance_support_radius=1)
    return p

def features(rgb):
    """8-bit Y/Co/Cg; only chroma averaged, all declared pixels retained.

    The 3x3 window replicates ROI border pixels. This is not ROI erosion.
    The RTL contract receives these same nine-pixel windows upstream.
    """
    a=rgb.astype(np.int32);r,g,b=np.moveaxis(a,-1,0)
    y=(r+2*g+b+2)>>2;co=(r-b+256)>>1;cg=(-r+2*g-b+512)>>2
    def mean3(v):
        p=np.pad(v,1,mode='edge');total=np.zeros(v.shape,np.int32)
        for j in range(3):
            for i in range(3):total+=p[j:j+v.shape[0],i:i+v.shape[1]]
        return (total+4)//9
    return np.stack([y,mean3(co),mean3(cg)],axis=-1).astype(np.uint8)

def window_metric(reference,current,edge,high=18,low=9):
    """Bit-exact metric on already normalized, paired RGB windows."""
    residual=np.abs(features(reference).astype(np.int16)-features(current).astype(np.int16)).max(axis=-1).astype(np.uint8)
    def chroma(a):
        r,g,b=np.moveaxis(a.astype(np.int16),-1,0)
        return np.stack([(r-b+256)>>1,(-r+2*g-b+512)>>2],axis=-1)
    rc=chroma(reference);cc=chroma(current);p=np.pad(rc,((2,2),(2,2),(0,0)),mode='edge');lo=np.full_like(rc,255);hi=np.zeros_like(rc)
    for j in range(5):
        for i in range(5):
            v=p[j:j+rc.shape[0],i:i+rc.shape[1]];lo=np.minimum(lo,v);hi=np.maximum(hi,v)
    # Restore thin color-only changes when they exceed reference chroma variation.
    # The variation allowance is measured from the good reference, never current.
    excess=np.maximum(np.abs(rc-cc)-(hi-lo),0).max(axis=-1).astype(np.uint8)
    residual=np.maximum(residual,excess)
    return residual,residual.astype(np.int16)>np.asarray(high,np.int16)+edge.astype(np.int16),residual.astype(np.int16)>np.asarray(low,np.int16)+(edge.astype(np.int16)>>1)

def compare(reference,current,p=None):
    p=policy() if p is None else p;started=time.perf_counter()
    if p!=policy():raise ValueError('Unsupported V166 policy; use a new audited implementation')
    if reference.shape!=(720,1280,3) or current.shape!=reference.shape or reference.dtype!=np.uint8 or current.dtype!=np.uint8:raise ValueError('Expected native720p uint8 RGB frames')
    result=dict(version=p['version'],scope=p['scope'],metric=p['metric'],accuracy_qualified=False,board_integrated=False,manual_review_required=True,roi=p['roi'],declared_roi_pixels=250000,inspected_pixels=0,alarm=None)
    def reject(reason):
        result.update(status='REJECTED_INPUT',decision='REVIEW_INPUT_OR_EXTENSIVE_SURFACE_CHANGE',reason=reason,seconds=time.perf_counter()-started)
        return result,None,None
    registration,error=base.register(reference,current,p);result['registration']=registration
    if error:return reject(error)
    x0,y0,x1,y1=p['roi'];yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
    aligned=np.clip(np.rint(base._sample(current,xx+registration['dx'],yy+registration['dy'])),0,255).astype(np.uint8)
    ref,transfer=base.matched_reference(reference,registration['dx'],registration['dy'],p);result['resampling_transfer']=transfer
    saturation=np.any((ref>8)&(ref<247)&((aligned<=1)|(aligned>=254)),axis=-1);result['new_saturation_fraction']=float(saturation.mean())
    if saturation.mean()>p['maximum_new_saturation_fraction']:return reject('new_clipping_or_specular_saturation')
    fit,error=base.photometric(ref,aligned,p);result['photometric']=fit
    if error:return reject(error)
    edge=base.edge_tolerance(reference,p);ep=np.pad(edge,1,mode='edge')
    edge=np.maximum.reduce([ep[j:j+500,i:i+500] for j in range(3) for i in range(3)])
    normalized,_,_,_=base.integer_difference(ref,aligned,fit['gain_q8'],fit['offset_integer'],edge,p['high'],p['low'])
    residual,strong,weak=window_metric(ref,normalized,edge,p['high'],p['low']);result['inspected_pixels']=250000
    result['residual']=dict(median=float(np.median(residual)),p90=float(np.percentile(residual,90)),strong_fraction=float(strong.mean()))
    if result['residual']['median']>p['maximum_median_residual'] or result['residual']['p90']>p['maximum_p90_residual'] or strong.mean()>p['maximum_strong_fraction']:return reject('extensive_surface_change_or_unqualified_reference')
    mask,regions=base.components(weak,strong,p)
    result.update(status='COMPARED',decision='REFERENCE_CHANGE_CANDIDATE' if regions else 'NO_REFERENCE_CHANGE_CANDIDATE',alarm=bool(regions),candidate_pixels=int(mask.sum()),regions=regions,seconds=time.perf_counter()-started,classification_limit='Surface change, not semantic crack classification; low contrast and chroma changes within reference variation remain limitations')
    return result,mask,aligned

def implementation():
    return {name:base.sha(Path(__file__).with_name(name)) for name in ('reference_v166.py','reference_tile.py')}

def calibrate(image,material_id,destination):
    if not material_id or len(material_id)>80:raise ValueError('Provide a pattern ID up to80 characters')
    ref=base.read_frame(image);p=policy();destination=Path(destination)
    if destination.exists():raise FileExistsError('Calibration bundles are immutable')
    destination.mkdir(parents=True);Image.fromarray(ref).save(destination/'reference.png')
    record=dict(schema=2,material_id=material_id,reference_declaration='CALLER_IDENTIFIED_GOOD_NOT_AUTOMATICALLY_VERIFIED',source_image_sha256=base.sha(image),reference_sha256=base.sha(destination/'reference.png'),implementation_sha256=implementation(),policy=p,policy_sha256=hashlib.sha256(base.canonical(p)).hexdigest(),accuracy_qualified=False)
    record['bundle_sha256']=hashlib.sha256(base.canonical(record)).hexdigest()
    (destination/'calibration.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return record

def inspect(bundle,image,material_id):
    bundle=Path(bundle);record=json.loads((bundle/'calibration.json').read_text(encoding='utf8'));digest=record.pop('bundle_sha256')
    if hashlib.sha256(base.canonical(record)).hexdigest()!=digest or base.sha(bundle/'reference.png')!=record['reference_sha256']:raise ValueError('Calibration bundle integrity mismatch')
    if record['schema']!=2 or record['policy']!=policy() or record['implementation_sha256']!=implementation():raise ValueError('Calibration revision changed; create a new bundle')
    if material_id!=record['material_id']:raise ValueError('Pattern/material ID mismatch')
    result,mask,aligned=compare(base.read_frame(bundle/'reference.png'),base.read_frame(image));result.update(material_id=material_id,bundle_sha256=digest,input_sha256=base.sha(image));return result,mask,aligned

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    cal=sub.add_parser('calibrate');cal.add_argument('--image',required=True,type=Path);cal.add_argument('--material-id',required=True);cal.add_argument('--out',required=True,type=Path)
    ins=sub.add_parser('inspect');ins.add_argument('--bundle',required=True,type=Path);ins.add_argument('--image',required=True,type=Path);ins.add_argument('--material-id',required=True);ins.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    if a.command=='calibrate':print(json.dumps(calibrate(a.image,a.material_id,a.out),ensure_ascii=False));return
    result,mask,aligned=inspect(a.bundle,a.image,a.material_id);base.save_result(a.out,result,mask,aligned);print(json.dumps(result,ensure_ascii=False));raise SystemExit(3 if result['status']=='REJECTED_INPUT' else 0)

if __name__=='__main__':main()
