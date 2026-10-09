"""OFFLINE candidate: same radius-8 seeds, radius-8/16 weak support.

No runtime host import. All thresholds, seed origins, growth depth and support
are fixed; a larger-scale response can connect to a seed but cannot create one.
"""
import numpy as np
from weak_reference import grow

def wide_weak_mask(narrow, wide, roi):
    narrow,wide,roi=np.asarray(narrow),np.asarray(wide),np.asarray(roi)
    if narrow.ndim!=2 or narrow.shape!=wide.shape or narrow.shape!=roi.shape or roi.dtype!=bool:
        raise ValueError('Expected same-shaped two-dimensional responses and boolean ROI')
    mask=(narrow>90)&roi
    weak=((narrow>45)|(wide>45))&roi
    for _ in range(4):mask=grow(mask,weak,3)
    return mask
