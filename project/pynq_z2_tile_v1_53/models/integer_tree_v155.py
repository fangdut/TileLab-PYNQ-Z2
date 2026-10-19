"""Portable integer tree oracle. This module is never a live host detector."""
import numpy as np
from tree_features_v155 import FEATURE_NAMES

def validate(model):
    keys=('feature','threshold','left','right','score');n=len(model['feature'])
    if not 1<=n<=255 or any(len(model[k])!=n for k in keys):raise ValueError('Invalid tree arrays')
    if tuple(model['features'])!=FEATURE_NAMES:raise ValueError('Feature contract mismatch')
    visited=set();stack=[(0,0)];maximum=0
    while stack:
        i,depth=stack.pop()
        if i in visited or not 0<=i<n or depth>12:raise ValueError('Repeated node, cycle or excessive depth')
        visited.add(i);maximum=max(maximum,depth)
        if not isinstance(model['score'][i],int) or not 0<=model['score'][i]<=255:raise ValueError('Invalid integer score')
        f=model['feature'][i]
        if f<0:
            if model['left'][i]!=-1 or model['right'][i]!=-1:raise ValueError('Invalid leaf')
        else:
            if not 0<=f<len(FEATURE_NAMES) or not isinstance(model['threshold'][i],int) or not 0<=model['threshold'][i]<=255:raise ValueError('Invalid comparison')
            stack.extend([(model['left'][i],depth+1),(model['right'][i],depth+1)])
    if len(visited)!=n:raise ValueError('Unreachable node')
    return maximum

def predict(features,model):
    depth=validate(model);a=np.asarray(features)
    if a.dtype!=np.uint8 or a.shape[-1]!=len(FEATURE_NAMES):raise ValueError('Expected uint8 feature vectors')
    x=a.reshape(-1,len(FEATURE_NAMES));node=np.zeros(len(x),np.int16)
    f=np.asarray(model['feature']);t=np.asarray(model['threshold']);left=np.asarray(model['left']);right=np.asarray(model['right'])
    for _ in range(depth):
        active=np.flatnonzero(f[node]>=0)
        if not len(active):break
        old=node[active];le=x[active,f[old]]<=t[old];node[active]=np.where(le,left[old],right[old])
    if np.any(f[node]>=0):raise AssertionError('Incomplete tree traversal')
    return np.asarray(model['score'],np.uint8)[node].reshape(a.shape[:-1])
