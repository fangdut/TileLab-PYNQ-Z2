"""Per-pattern good-reference prototype. Offline only; no fitting a new model.

All500x500 declared pixels are inspected. Alignment samples may use the full
camera frame and surrounding tile boundary; inspection never crops away edges.
Rejected input has alarm=None and no mask: it must never be counted as a good tile.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_frame(path):
    with Image.open(path) as im:
        if im.size!=(1280,720):raise ValueError('Reference mode requires native1280x720 RGB with alignment context; no silent resize/padding')
        return np.array(im.convert('RGB'))

def policy():return json.loads((ROOT/'config/reference_v165.json').read_text(encoding='utf8'))

def _gray(a):return ((a[...,0].astype(np.int32)*77+a[...,1].astype(np.int32)*150+a[...,2].astype(np.int32)*29)>>8).astype(np.float32)

def _mean(a,r=3):
    p=np.pad(a.astype(np.float64),r,mode='edge');i=np.pad(p,((1,0),(1,0))).cumsum(0).cumsum(1);s=2*r+1
    return ((i[s:,s:]-i[:-s,s:]-i[s:,:-s]+i[:-s,:-s])/(s*s)).astype(np.float32)

def _sample(a,x,y):
    x,y=np.broadcast_arrays(np.asarray(x),np.asarray(y));ix=np.floor(x).astype(np.int32);iy=np.floor(y).astype(np.int32)
    if ix.min()<0 or iy.min()<0 or ix.max()+1>=a.shape[1] or iy.max()+1>=a.shape[0]:raise ValueError('Alignment would require unavailable camera pixels')
    fx=x-ix;fy=y-iy
    if a.ndim==3:fx=fx[...,None];fy=fy[...,None]
    return ((1-fx)*(1-fy)*a[iy,ix]+fx*(1-fy)*a[iy,ix+1]+(1-fx)*fy*a[iy+1,ix]+fx*fy*a[iy+1,ix+1]).astype(np.float32)

def _ncc(a,b):
    a=a-a.mean();b=b-b.mean();den=np.sqrt(np.mean(a*a)*np.mean(b*b))
    return float(np.mean(a*b)/den) if den>1e-5 else 0.

def register(reference,current,p):
    rg=_gray(reference);cg=_gray(current);rh=rg-_mean(rg);ch=cg-_mean(cg)
    x0,y0,x1,y1=p['roi'];yi,xi=np.mgrid[y0+12:y1-11:4,x0+12:x1-11:4];yh,xh=np.mgrid[y0-8:y1+9:4,x0-8:x1+9:4]
    ri=rh[yi,xi];rr=rh[yh,xh];textured=float(ri.std())>=2.
    def score(dx,dy):
        outer=_ncc(rr,_sample(ch,xh+dx,yh+dy))
        return .85*_ncc(ri,_sample(ch,xi+dx,yi+dy))+.15*outer if textured else outer
    search=p['search_shift_px'];candidates=[(score(dx,dy),dx,dy) for dy in range(-search,search+1) for dx in range(-search,search+1)]
    best=max(candidates,key=lambda t:(t[0],-abs(t[1])-abs(t[2])));initial=best
    for step in (.5,.25,.125,.0625):
        s,dx,dy=best;best=max((score(dx+ox,dy+oy),dx+ox,dy+oy) for oy in (-step,0,step) for ox in (-step,0,step))
    s,dx,dy=best
    rivals=[v[0] for v in candidates if max(abs(v[1]-dx),abs(v[2]-dy))>=2.]
    result=dict(dx=dx,dy=dy,correlation=s,peak_margin=s-max(rivals),texture_mode='pattern_and_boundary' if textured else 'fixture_boundary',quadrant_drifts=[])
    if s<p['minimum_registration_correlation']:return result,'registration_mismatch'
    if max(abs(dx),abs(dy))>p['allowed_shift_px']:return result,'translation_exceeds_fixture_tolerance'
    if result['peak_margin']<p['minimum_peak_margin']:return result,'ambiguous_registration'
    # A translation must also agree locally. Rotation/warp is rejected rather
    # than concealed by an increasingly flexible per-image deformation.
    for ylo,yhi in [(y0+12,(y0+y1)//2),((y0+y1)//2,y1-11)]:
        for xlo,xhi in [(x0+12,(x0+x1)//2),((x0+x1)//2,x1-11)]:
            yy,xx=np.mgrid[ylo:yhi:4,xlo:xhi:4];rrq=rh[yy,xx]
            if rrq.std()<2:continue
            q=max((_ncc(rrq,_sample(ch,xx+dx+ox,yy+dy+oy)),ox,oy) for oy in (-1.,-.5,0.,.5,1.) for ox in (-1.,-.5,0.,.5,1.))
            result['quadrant_drifts'].append(dict(dx=q[1],dy=q[2],correlation=q[0]))
    if any(max(abs(q['dx']),abs(q['dy']))>p['maximum_quadrant_drift_px'] or q['correlation']<.75 for q in result['quadrant_drifts']):return result,'non_translation_geometry_or_local_mismatch'
    return result,None

def edge_tolerance(reference,p):
    x0,y0,x1,y1=p['roi'];lo=np.full((500,500,3),255,np.int16);hi=np.zeros_like(lo)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            v=reference[y0+dy:y1+dy+1,x0+dx:x1+dx+1].astype(np.int16);lo=np.minimum(lo,v);hi=np.maximum(hi,v)
    return np.minimum(p['edge_tolerance_cap'],(hi-lo).max(axis=-1)//4).astype(np.uint8)

def photometric(reference,current,p):
    gains=[];offsets=[];modes=[]
    for c in range(3):
        x=current[::2,::2,c].astype(np.float64).ravel();y=reference[::2,::2,c].astype(np.float64).ravel();valid=(x>3)&(x<252)&(y>11)&(y<244);x=x[valid];y=y[valid]
        if len(x)<1000:return None,'insufficient_photometric_information'
        if min(x.std(),y.std())<2:g=1.;b=float(np.median(y-x));mode='offset_only'
        else:
            g=float((np.percentile(y,90)-np.percentile(y,10))/max(1.,np.percentile(x,90)-np.percentile(x,10)));b=float(np.median(y-g*x));mode='robust_affine'
            for _ in range(5):
                residual=y-g*x-b;center=np.median(residual);mad=np.median(np.abs(residual-center));keep=np.abs(residual-center)<=max(4.,3.*1.4826*mad)
                xx=x[keep];yy=y[keep];xm=xx.mean();ym=yy.mean();variance=np.mean((xx-xm)**2)
                if variance<1:return None,'unstable_photometric_fit'
                g=float(np.mean((xx-xm)*(yy-ym))/variance);b=float(ym-g*xm)
        if not(p['minimum_gain']<=g<=p['maximum_gain']) or abs(b)>p['maximum_offset']:return dict(gains=gains+[g],offsets=offsets+[b]),'illumination_out_of_range'
        gains.append(g);offsets.append(b);modes.append(mode)
    return dict(gains=gains,offsets=offsets,gain_q8=np.rint(np.array(gains)*256).astype(int).tolist(),offset_integer=np.rint(offsets).astype(int).tolist(),fit_modes=modes),None

def integer_difference(reference,current,gain_q8,offset,edge,high=18,low=9):
    """Bit-exact contract for reference_difference_v165.v, ordinaryRGB order."""
    a=current.astype(np.int32);g=np.asarray(gain_q8,np.int32);b=np.asarray(offset,np.int32)
    normalized=np.clip(((a*g+128)>>8)+b,0,255).astype(np.uint8)
    residual=np.abs(reference.astype(np.int16)-normalized.astype(np.int16)).max(axis=-1).astype(np.uint8)
    return normalized,residual,residual.astype(np.int16)>high+edge.astype(np.int16),residual.astype(np.int16)>low+(edge.astype(np.int16)>>1)

def components(weak,strong,p):
    """Run-length8-connected regions; no SciPy or unbounded pixel recursion."""
    parents=[];runs=[];previous=[]
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for y,row in enumerate(weak):
        change=np.diff(np.pad(row.astype(np.int8),(1,1)));starts=np.flatnonzero(change==1);ends=np.flatnonzero(change==-1)-1;present=[];j=0
        for x0,x1 in zip(starts,ends):
            i=len(parents);parents.append(i);runs.append((y,int(x0),int(x1),int(strong[y,x0:x1+1].sum())));present.append((int(x0),int(x1),i))
            while j<len(previous) and previous[j][1]<x0-1:j+=1
            k=j
            while k<len(previous) and previous[k][0]<=x1+1:
                a=find(i);b=find(previous[k][2]);parents[a]=b;k+=1
        previous=present
    groups={}
    for i,(y,x0,x1,seeds) in enumerate(runs):
        root=find(i);g=groups.setdefault(root,dict(area=0,seeds=0,x0=500,y0=500,x1=0,y1=0,ids=[]));g['area']+=x1-x0+1;g['seeds']+=seeds;g['x0']=min(g['x0'],x0);g['y0']=min(g['y0'],y);g['x1']=max(g['x1'],x1);g['y1']=max(g['y1'],y);g['ids'].append(i)
    mask=np.zeros(weak.shape,bool);regions=[]
    for g in groups.values():
        span=max(g['x1']-g['x0']+1,g['y1']-g['y0']+1)
        if g['area']<p['minimum_component_pixels'] or span<p['minimum_component_span'] or g['seeds']<p['minimum_component_seeds']:continue
        for i in g['ids']:
            y,x0,x1,_=runs[i];mask[y,x0:x1+1]=True
        kind='thin_surface_change' if g['area']/span<=12 and g['area']/((g['x1']-g['x0']+1)*(g['y1']-g['y0']+1))<.5 else 'broad_surface_change'
        regions.append(dict(box=[g['x0']+390,g['y0']+110,g['x1']+390,g['y1']+110],pixels=g['area'],seeds=g['seeds'],kind=kind))
    return mask,regions

def compare(reference,current,p=None):
    p=policy() if p is None else p;started=time.perf_counter()
    if reference.shape!=(720,1280,3) or current.shape!=reference.shape or reference.dtype!=np.uint8 or current.dtype!=np.uint8:raise ValueError('Expected two native720p uint8 RGB frames')
    result=dict(version=p['version'],scope=p['scope'],accuracy_qualified=False,board_integrated=False,manual_review_required=True,roi=p['roi'],inspected_pixels=250000,alarm=None)
    def reject(reason):result.update(status='REJECTED_INPUT',decision='REVIEW_INPUT_OR_EXTENSIVE_SURFACE_CHANGE',reason=reason,seconds=time.perf_counter()-started);return result,None,None
    registration,error=register(reference,current,p);result['registration']=registration
    if error:return reject(error)
    x0,y0,x1,y1=p['roi'];yy,xx=np.mgrid[y0:y1+1,x0:x1+1];aligned=np.clip(np.rint(_sample(current,xx+registration['dx'],yy+registration['dy'])),0,255).astype(np.uint8);ref=reference[y0:y1+1,x0:x1+1]
    saturation=np.any((ref>8)&(ref<247)&((aligned<=1)|(aligned>=254)),axis=-1);result['new_saturation_fraction']=float(saturation.mean())
    if saturation.mean()>p['maximum_new_saturation_fraction']:return reject('new_clipping_or_specular_saturation')
    fit,error=photometric(ref,aligned,p);result['photometric']=fit
    if error:return reject(error)
    edge=edge_tolerance(reference,p);normalized,residual,strong,weak=integer_difference(ref,aligned,fit['gain_q8'],fit['offset_integer'],edge,p['high'],p['low'])
    result['residual']=dict(median=float(np.median(residual)),p90=float(np.percentile(residual,90)),strong_fraction=float(strong.mean()))
    if result['residual']['median']>p['maximum_median_residual'] or result['residual']['p90']>p['maximum_p90_residual'] or strong.mean()>p['maximum_strong_fraction']:return reject('extensive_surface_change_or_unqualified_reference')
    mask,regions=components(weak,strong,p);result.update(status='COMPARED',decision='REFERENCE_CHANGE_CANDIDATE' if regions else 'NO_REFERENCE_CHANGE_CANDIDATE',alarm=bool(regions),candidate_pixels=int(mask.sum()),regions=regions,seconds=time.perf_counter()-started,classification_limit='Surface change only; cannot prove semantic crack versus stain, dirt, glaze change or printing defect')
    return result,mask,aligned

def calibrate(image,material_id,destination):
    if not material_id or len(material_id)>80:raise ValueError('Provide a nonempty material/pattern ID up to80 characters')
    ref=read_frame(image);p=policy();destination=Path(destination)
    if destination.exists():raise FileExistsError('Calibration bundles are immutable; use a new path/revision')
    destination.mkdir(parents=True);Image.fromarray(ref).save(destination/'reference.png');Image.fromarray(edge_tolerance(ref,p)).save(destination/'edge_tolerance.png')
    record=dict(schema=1,material_id=material_id,reference_declaration='CALLER_IDENTIFIED_GOOD_NOT_AUTOMATICALLY_VERIFIED',source_image_sha256=sha(image),reference_sha256=sha(destination/'reference.png'),edge_tolerance_sha256=sha(destination/'edge_tolerance.png'),policy=p,policy_sha256=hashlib.sha256(canonical(p)).hexdigest(),accuracy_qualified=False)
    record['bundle_sha256']=hashlib.sha256(canonical(record)).hexdigest();(destination/'calibration.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return record

def inspect(bundle,image,material_id):
    bundle=Path(bundle);record=json.loads((bundle/'calibration.json').read_text(encoding='utf8'));digest=record.pop('bundle_sha256')
    if hashlib.sha256(canonical(record)).hexdigest()!=digest or sha(bundle/'reference.png')!=record['reference_sha256'] or sha(bundle/'edge_tolerance.png')!=record['edge_tolerance_sha256']:raise ValueError('Calibration bundle integrity mismatch')
    if record['policy']!=policy():raise ValueError('Calibration policy differs from the current fixed prototype; recalibrate a new revision')
    if material_id!=record['material_id']:raise ValueError('Explicit pattern/material ID differs from the good reference')
    result,mask,aligned=compare(read_frame(bundle/'reference.png'),read_frame(image),record['policy']);result.update(material_id=material_id,bundle_sha256=digest,input_sha256=sha(image));return result,mask,aligned

def save_result(destination,result,mask,aligned):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);(destination/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if mask is not None:
        Image.fromarray(mask.astype(np.uint8)*255).save(destination/'mask.png');overlay=aligned.copy();overlay[mask]=overlay[mask]//2+np.array([127,0,0],np.uint8);im=Image.fromarray(overlay);draw=ImageDraw.Draw(im)
        for r in result['regions']:
            x0,y0,x1,y1=r['box'];draw.rectangle([x0-390,y0-110,x1-390,y1-110],outline='red',width=2)
        im.save(destination/'overlay.png');Image.fromarray(aligned).save(destination/'aligned.png')

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    cal=sub.add_parser('calibrate');cal.add_argument('--image',required=True,type=Path);cal.add_argument('--material-id',required=True);cal.add_argument('--out',required=True,type=Path)
    ins=sub.add_parser('inspect');ins.add_argument('--bundle',required=True,type=Path);ins.add_argument('--image',required=True,type=Path);ins.add_argument('--material-id',required=True);ins.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    if a.command=='calibrate':print(json.dumps(calibrate(a.image,a.material_id,a.out),ensure_ascii=False));return
    result,mask,aligned=inspect(a.bundle,a.image,a.material_id);save_result(a.out,result,mask,aligned);print(json.dumps(result,ensure_ascii=False));raise SystemExit(3 if result['status']=='REJECTED_INPUT' else 0)

if __name__=='__main__':main()
