"""Estimate illumination from reference-intensity strata, not noise in flats.

A dominant flat ink color must not turn JPEG/noise variance into a gain and
large offset. Conditional medians across populated reference levels preserve
minor printed colors without allowing changed pixels to set normal tolerance.
"""
import numpy as np
def fit(reference,current,p):
    gains=[];offsets=[];modes=[];levels=[]
    padded=np.pad(reference,((1,1),(1,1),(0,0)),mode='edge');lo=reference.copy();hi=reference.copy()
    for j in range(3):
        for i in range(3):
            v=padded[j:j+reference.shape[0],i:i+reference.shape[1]];lo=np.minimum(lo,v);hi=np.maximum(hi,v)
    local_span=hi.astype(np.int16)-lo.astype(np.int16)
    for c in range(3):
        # Fixture/background mixing at the physical border is not illumination
        # information. Only parameter estimation samples an 8px inset; the
        # FPGA still scores every pixel of the complete 500x500 surface.
        x=current[8:-8:2,8:-8:2,c].astype(np.float64).ravel();y=reference[8:-8:2,8:-8:2,c].astype(np.float64).ravel();valid=(x>3)&(x<252)&(y>11)&(y<244)
        # JPEG/subpixel mixing at printed edges is spatially varying and is
        # not a global RGB exposure change. Estimate from reference-flat
        # interiors when enough samples exist; current defects cannot select
        # or enlarge this reference-only sample mask.
        flat=local_span[8:-8:2,8:-8:2,c].ravel()<=p['photometric_reference_flatness_span']
        if int((valid&flat).sum())>=1000:valid&=flat
        x=x[valid];y=y[valid]
        if len(x)<1000:return None,'insufficient_photometric_information'
        xx=[];yy=[]
        for low in range(0,256,16):
            chosen=(y>=low)&(y<low+16)
            if int(chosen.sum())>=128:xx.append(float(np.median(x[chosen])));yy.append(float(np.median(y[chosen])))
        xx=np.array(xx);yy=np.array(yy);mode='reference_stratified_affine';levels.append(len(xx))
        if len(xx)<2 or np.ptp(yy)<12 or np.ptp(xx)<8:
            g=1.;b=float(np.median(y-x));mode='offset_only_unidentified_gain'
        else:
            keep=np.ones(len(xx),bool);g=1.;b=float(np.median(yy-xx))
            for _ in range(5):
                xv=xx[keep];yv=yy[keep];xm=xv.mean();ym=yv.mean();variance=np.mean((xv-xm)**2)
                if variance<4:g=1.;b=float(np.median(y-x));mode='offset_only_unidentified_gain';break
                g=float(np.mean((xv-xm)*(yv-ym))/variance);b=float(ym-g*xm)
                residual=yy-g*xx-b;center=np.median(residual);mad=np.median(np.abs(residual-center));next_keep=np.abs(residual-center)<=max(4.,3.*1.4826*mad)
                if int(next_keep.sum())<2 or np.array_equal(next_keep,keep):break
                keep=next_keep
        if not(p['minimum_gain']<=g<=p['maximum_gain']) or abs(b)>p['maximum_offset']:return dict(gains=gains+[g],offsets=offsets+[b],fit_modes=modes+[mode],populated_reference_levels=levels),'illumination_out_of_range'
        gains.append(g);offsets.append(b);modes.append(mode)
    return dict(gains=gains,offsets=offsets,gain_q8=np.rint(np.array(gains)*256).astype(int).tolist(),offset_integer=np.rint(offsets).astype(int).tolist(),fit_modes=modes,populated_reference_levels=levels),None
