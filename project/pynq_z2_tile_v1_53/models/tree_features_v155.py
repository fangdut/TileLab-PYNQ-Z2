"""Integer local features for a small FPGA-oriented tree experiment, offline only."""
import numpy as np
from ridge_reference import shifted
FEATURE_NAMES=('valley8','valley16','mean7_offset2','mean15_offset4','mean7_offset4','mean15_offset8','gray','background8','short_direction_margin','long_direction_margin','direction_agreement','short_shoulder_noise')

def feature_matrix(gray,n,w,s,l,s4,l8,noise):
    a=np.asarray(gray,dtype=np.int32)
    background=sum(shifted(a,dx,dy) for dx,dy in [(4,0),(-4,0),(0,4),(0,-4),(8,0),(-8,0),(0,8),(0,-8)])>>3
    ss=np.sort(s,axis=0);ll=np.sort(l,axis=0);direction=np.argmax(s,axis=0)
    directional_noise=np.take_along_axis(noise,direction[None,:,:],axis=0)[0]
    return np.stack([n,w,ss[-1],ll[-1],s4.max(axis=0),l8.max(axis=0),a,background,
                     ss[-1]-ss[-2],ll[-1]-ll[-2],(direction==np.argmax(l,axis=0)).astype(np.uint8)*255,directional_noise],axis=-1).astype(np.uint8)
