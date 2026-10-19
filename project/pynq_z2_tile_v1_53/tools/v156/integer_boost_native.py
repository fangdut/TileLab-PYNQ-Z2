"""Optional portable C accelerator for offline integer verification only."""
from pathlib import Path
import ctypes
import numpy as np
from integer_boost_reference import validate

class NativeBoost:
    def __init__(self,model,library):
        validate(model);self.model=model
        f=[];threshold=[];left=[];right=[];value=[];roots=[]
        for tree in model['trees']:
            offset=len(f);roots.append(offset)
            for node in tree:
                f.append(-1 if node['leaf'] else node['feature']);threshold.append(node['threshold'] if not node['leaf'] else 0)
                left.append(offset+node['left']);right.append(offset+node['right']);value.append(node['value'])
        self.arrays=[np.array(a,dtype=d) for a,d in [(f,np.int16),(threshold,np.uint8),(left,np.int32),(right,np.int32),(value,np.int32),(roots,np.int32)]]
        self.dll=ctypes.CDLL(str(Path(library).resolve()));self.fn=self.dll.tile_boost_predict;self.fn.restype=None
        self.fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t]+[ctypes.c_void_p]*6+[ctypes.c_int,ctypes.c_int32,ctypes.c_void_p]
    def predict(self,features):
        a=np.asarray(features)
        if a.dtype!=np.uint8 or a.shape[-1]!=12:raise ValueError('Expected 12 uint8 features')
        x=np.ascontiguousarray(a.reshape(-1,12));out=np.empty(len(x),np.int32)
        self.fn(x.ctypes.data,len(x),*[v.ctypes.data for v in self.arrays],len(self.model['trees']),self.model['baseline'],out.ctypes.data)
        return out.reshape(a.shape[:-1])
