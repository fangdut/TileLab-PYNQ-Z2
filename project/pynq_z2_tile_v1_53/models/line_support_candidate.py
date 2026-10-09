"""OFFLINE CANDIDATE ONLY. No deployment, no live image classification.

Preserve existing >=3 accepted-neighbor growth. Additionally grow a weak center
along one of four opposed weak pairs when at least one end is accepted and the
3x3 weak population is <=5. Four cascades stay within four pixels of a seed.
"""
import numpy as np

def grow_line(mask,weak):
    if mask.dtype!=np.bool_ or weak.dtype!=np.bool_ or mask.ndim!=2 or mask.shape!=weak.shape:
        raise ValueError('Expected equally shaped two-dimensional Boolean masks')
    h,w=mask.shape;p=np.pad(mask,1);q=np.pad(weak,1)
    a=[p[y:y+h,x:x+w] for y in range(3) for x in range(3)]
    b=[q[y:y+h,x:x+w] for y in range(3) for x in range(3)]
    accepted_count=sum(v.astype(np.uint8) for v in a)
    weak_count=sum(v.astype(np.uint8) for v in b)
    line=np.zeros(mask.shape,bool)
    for left,right in ((3,5),(1,7),(0,8),(2,6)):
        line|=b[left]&b[right]&(a[left]|a[right])
    return mask | (weak & ((accepted_count>=3) | (line & (weak_count<=5))))
