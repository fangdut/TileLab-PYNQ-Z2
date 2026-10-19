"""Offline candidate: require dark-ridge contrast at three tangent positions.

Each directional 7+center average is tested at tangent offsets -2,0,+2.
The minimum of these three responses rejects isolated dark texture peaks.
All taps fit inside the existing 17x17 gray window (maximum offset 7).
"""
import numpy as np
from ridge_reference import shifted


def coherent_ridge_score(gray):
    a=np.asarray(gray,dtype=np.int32)
    if a.ndim!=2 or min(a.shape)<17 or np.any((a<0)|(a>255)):
        raise ValueError('Expected grayscale >=17x17, values 0..255')
    best=np.zeros_like(a)
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        mean=(sum(shifted(a,dx*k,dy*k) for k in range(-3,4))+a)>>3
        shoulder=np.minimum(shifted(mean,-2*dy,2*dx),shifted(mean,2*dy,-2*dx))
        response=np.maximum(shoulder-mean,0)
        response=np.minimum(response,np.minimum(shifted(response,-2*dx,-2*dy),shifted(response,2*dx,2*dy)))
        best=np.maximum(best,response)
    best[:8]=0;best[-8:]=0;best[:,:8]=0;best[:,-8:]=0
    return best.astype(np.uint8)
