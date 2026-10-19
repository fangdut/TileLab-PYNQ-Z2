"""Offline preprocessing and 12-byte feature contract; no live-host imports."""
import numpy as np
from PIL import Image
from valley_reference import valley
from directional_link_reference import direction_planes,shoulder_noise
from tree_features_v155 import feature_matrix

def from_gray_crop(g):
    n=valley(g,8);w=valley(g,16);s=direction_planes(g,8);l=direction_planes(g,16)
    s4=direction_planes(g,8,4);l8=direction_planes(g,16,8);noise=shoulder_noise(g)
    features=feature_matrix(g,n,w,s,l,s4,l8,noise);inside=np.zeros(g.shape,bool);inside[16:576,16:1136]=True
    return dict(n=n,w=w,s=s,l=l,s4=s4,features=features,inside=inside)

def industrial_strip(path):
    with Image.open(path) as im:a=np.asarray(im.rotate(-90,expand=True).convert('RGB')).astype(np.int32)
    gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8;g=np.zeros((592,1152),np.int32);g[168:424,16:1136]=gray[:,144:1264]
    return from_gray_crop(g)

def acquired_rgb(path):
    with Image.open(path) as im:a=np.asarray(im.convert('RGB')).astype(np.int32)
    if a.shape!=(720,1280,3):raise ValueError('Expected acquired 720p RGB frame')
    gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
    return from_gray_crop(gray[64:656,64:1216])

class RegionScorer:
    def __init__(self,backend):
        self.backend=backend;t=np.zeros((256,12),np.uint8);t[:,6]=np.arange(256);t[:,7]=np.arange(256);t[:,10]=255;self.table=backend.predict(t)
    def predict(self,features,inside):
        flat=features.reshape(-1,12);ids=np.flatnonzero(inside.ravel());x=flat[ids]
        constant=(~np.any(x[:,:6],axis=1))&(x[:,6]==x[:,7])&(x[:,8]==0)&(x[:,9]==0)&(x[:,10]==255)&(x[:,11]==0)
        values=np.empty(len(x),np.int32);values[constant]=self.table[x[constant,6]];values[~constant]=self.backend.predict(x[~constant])
        score=np.full(inside.shape,-1073741824,np.int32);score.ravel()[ids]=values;return score
