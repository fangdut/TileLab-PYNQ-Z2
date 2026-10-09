"""Strict bounded decoder for the board's lossless 32-bit-word transport."""
import struct
import numpy as np
import ctypes
from pathlib import Path
_native=None
try:
    _lib=ctypes.CDLL(str(Path(__file__).with_name('rle_decode.dll')))
    _native=_lib.tile_rle_decode
    _native.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32]
    _native.restype=ctypes.c_int
except OSError:
    pass

def decode(payload,expected_bytes):
    if expected_bytes<0 or expected_bytes%4 or len(payload)%4 or len(payload)>expected_bytes:
        raise ValueError('Invalid RLE byte length')
    words=np.frombuffer(payload,dtype='<u4');out=np.empty(expected_bytes//4,dtype='<u4')
    if _native is not None:
        if _native(words.ctypes.data,len(words),out.ctypes.data,len(out)):
            raise ValueError('Invalid or incomplete RLE frame')
        return out.tobytes()
    i=j=0
    while i<len(words):
        tag=int(words[i]);i+=1;count=tag&0x7fffffff
        if not count or count>len(out)-j:raise ValueError('Invalid RLE count')
        if tag&0x80000000:
            if i>=len(words):raise ValueError('Missing RLE repeat value')
            out[j:j+count]=words[i];i+=1
        else:
            if count>len(words)-i:raise ValueError('Truncated RLE literal')
            out[j:j+count]=words[i:i+count];i+=count
        j+=count
    if j!=len(out):raise ValueError('Incomplete RLE frame')
    return out.tobytes()
