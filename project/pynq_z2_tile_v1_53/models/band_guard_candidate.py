"""OFFLINE ONLY: normal weak growth plus a stricter lower-contrast bridge.

Normal weak pixels retain >=3 accepted-neighbor growth. Very-weak pixels may
join only with >=3 accepted neighbors including an opposed accepted pair.
"""
import numpy as np

def grow_band(mask,weak,very_weak):
    if any(v.dtype!=np.bool_ or v.ndim!=2 or v.shape!=mask.shape for v in (mask,weak,very_weak)):
        raise ValueError('Expected equally shaped two-dimensional Boolean masks')
    h,w=mask.shape;p=np.pad(mask,1)
    a=[p[y:y+h,x:x+w] for y in range(3) for x in range(3)]
    count=sum(v.astype(np.uint8) for v in a)
    opposed=(a[3]&a[5])|(a[1]&a[7])|(a[0]&a[8])|(a[2]&a[6])
    return mask | ((count>=3)&(weak|(very_weak&opposed)))
