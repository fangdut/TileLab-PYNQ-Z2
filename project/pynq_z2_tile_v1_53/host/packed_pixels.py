"""Strict lossless BGR24 + one-bit mask reconstruction to canonical BGRM32."""
import numpy as np

def decode(payload,expected_bytes):
    if type(expected_bytes) is not int or expected_bytes<0 or expected_bytes%4:
        raise ValueError('Invalid packed pixel byte length')
    n=expected_bytes//4
    if len(payload)!=3*n+(n+7)//8:
        raise ValueError('Invalid packed pixel payload length')
    data=np.frombuffer(payload,dtype=np.uint8)
    if n%8 and int(data[-1])>>(n%8):
        raise ValueError('Nonzero packed mask padding')
    out=np.empty((n,4),dtype=np.uint8)
    out[:,:3]=data[:3*n].reshape(n,3)
    out[:,3]=np.unpackbits(data[3*n:],bitorder='little')[:n]
    return out.tobytes()
