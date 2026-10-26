"""Integer global histogram equalization; offline oracle for the PL unit."""
import numpy as np
def equalize(gray):
    gray=np.asarray(gray,dtype=np.uint8);hist=np.bincount(gray.ravel(),minlength=256);first=int(np.flatnonzero(hist)[0]);den=gray.size-int(hist[first])
    if not den:return gray.copy()
    cdf=np.maximum(hist.cumsum()-hist[first],0);num=cdf*255;q=num//den;r=num%den
    lut=(q+((2*r>den)|((2*r==den)&((q&1)!=0)))).astype('uint8')
    return lut[gray]
def packed_channels(gray):
    gray=np.asarray(gray,dtype=np.uint8);eq=equalize(gray);add=np.minimum(gray.astype('u2')+eq,255).astype('u1')
    return ((gray.astype('u4')<<16)|(eq.astype('u4')<<8)|add.astype('u4')).astype('<u4')
