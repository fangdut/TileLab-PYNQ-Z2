"""Fixture-boundary pose, followed by interior-pattern identity verification.

One-directional prints cannot determine motion along the stripe. The physical
tile edges supply both axes independently; local tie scores prefer zero drift.
All inspected pixels remain in the declared ROI.
"""
import numpy as np
import reference_tile as base
def register(reference,current,p):
    rg=base._gray(reference);cg=base._gray(current);rh=rg-base._mean(rg);ch=cg-base._mean(cg)
    x0,y0,x1,y1=p['roi'];radius=24;normal=np.arange(-10,11,dtype=float)
    def profiles(a,axis):
        if axis==0:return [a[y0+24:y1-23,c-radius:c+radius+1].mean(axis=0) for c in (x0,x1)]
        return [a[c-radius:c+radius+1,x0+24:x1-23].mean(axis=1) for c in (y0,y1)]
    def ncc(a,b):
        a=a-a.mean();b=b-b.mean();den=np.sqrt(np.mean(a*a)*np.mean(b*b));return float(np.mean(a*b)/den) if den>1e-5 else 0.
    def solve(r,c):
        observed=[v[radius-10:radius+11] for v in c]
        def side(shift,i):return ncc(np.interp(radius+normal-shift,np.arange(49),r[i]),observed[i])
        def score(shift):return sum(side(shift,i) for i in (0,1))*.5
        integer=[(score(s),float(s)) for s in range(-8,9)];best=max(integer,key=lambda t:(t[0],-abs(t[1])))
        center=best[1];best=max((score(s),float(s)) for s in np.arange(center-1.5,center+1.501,.25))
        for step in (.125,.0625):
            center=best[1];best=max((score(center+o),center+o) for o in (-step,0,step))
        score_value,shift=best;drifts=[]
        for i in (0,1):
            candidates=[(side(shift+o,i),o) for o in (-1.,-.5,0.,.5,1.)];top=max(c[0] for c in candidates);chosen=min((c for c in candidates if c[0]>=top-1e-5),key=lambda c:abs(c[1]));drifts.append(dict(correlation=side(shift,i),drift=chosen[1]))
        rivals=[v[0] for v in integer if abs(v[1]-shift)>=2]
        return dict(shift=shift,correlation=score_value,peak_margin=score_value-max(rivals),edges=drifts)
    axes=[solve(profiles(rh,axis),profiles(ch,axis)) for axis in (0,1)];dx=axes[0]['shift'];dy=axes[1]['shift']
    result=dict(dx=dx,dy=dy,correlation=min(a['correlation'] for a in axes),peak_margin=min(a['peak_margin'] for a in axes),texture_mode='independent_physical_boundary_axes_then_pattern_identity',boundary_axes=axes,quadrant_drifts=[])
    if result['correlation']<p['minimum_registration_correlation']:return result,'fixture_boundary_mismatch'
    if max(abs(dx),abs(dy))>p['allowed_shift_px']:return result,'translation_exceeds_fixture_tolerance'
    if result['peak_margin']<p['minimum_peak_margin']:return result,'ambiguous_fixture_boundary'
    if any(e['correlation']<.88 or abs(e['drift'])>p['maximum_quadrant_drift_px'] for a in axes for e in a['edges']):return result,'inconsistent_tile_edges'
    yi,xi=np.mgrid[y0+12:y1-11:4,x0+12:x1-11:4];ri=rh[yi,xi];textured=float(ri.std())>=2.
    pattern=base._ncc(base._sample(rh,xi-dx,yi-dy),ch[yi,xi]) if textured else None;result['pattern_correlation']=pattern
    if textured and pattern<p['minimum_registration_correlation']:return result,'reference_pattern_mismatch'
    for ylo,yhi in [(y0+12,(y0+y1)//2),((y0+y1)//2,y1-11)]:
        for xlo,xhi in [(x0+12,(x0+x1)//2),((x0+x1)//2,x1-11)]:
            yy,xx=np.mgrid[ylo:yhi:4,xlo:xhi:4];rrq=rh[yy,xx]
            if rrq.std()<2:continue
            cq=ch[yy,xx];candidates=[(base._ncc(base._sample(rh,xx-dx-ox,yy-dy-oy),cq),ox,oy) for oy in (-1.,-.5,0.,.5,1.) for ox in (-1.,-.5,0.,.5,1.)]
            top=max(c[0] for c in candidates);q=min((c for c in candidates if c[0]>=top-1e-5),key=lambda c:c[1]*c[1]+c[2]*c[2]);result['quadrant_drifts'].append(dict(dx=q[1],dy=q[2],correlation=q[0]))
    if any(max(abs(q['dx']),abs(q['dy']))>p['maximum_quadrant_drift_px'] or q['correlation']<.75 for q in result['quadrant_drifts']):return result,'non_translation_geometry_or_local_mismatch'
    return result,None
