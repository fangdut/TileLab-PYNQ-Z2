"""Bind generated firmware constants to actual model bytes, not stale headers."""
from pathlib import Path
import hashlib,json,struct,zlib
def load_identity(profile):
    profile=Path(profile);graph=json.loads((profile/'graph.json').read_text(encoding='utf8'));blob=(profile/'model.bin').read_bytes()
    if len(blob)<256:raise ValueError('Truncated model header')
    h=struct.unpack_from('<64I',blob)
    expected=dict(sha256=hashlib.sha256(blob).hexdigest(),crc32=zlib.crc32(blob),model_bytes=len(blob),grid=h[4],steps=h[2],workspace_bytes=h[16])
    if h[0]!=0x17000001 or h[1]!=len(blob) or not 1<=h[4]<=28:raise ValueError('Invalid model identity header')
    for key,value in expected.items():
        if graph.get(key)!=value:raise ValueError('Model identity mismatch: '+key)
    roi=graph.get('input_roi')
    roi_header=tuple(roi[k] for k in ['x','y','width','height','source_width','source_height'])+(0x19600001,) if roi else (0,)*7
    if tuple(h[20:27])!=roi_header:raise ValueError('Model identity mismatch: ROI header')
    header=f'#define MODEL_BYTES {len(blob)}u\n#define MODEL_CRC {expected["crc32"]}u\n#define MODEL_GRID {h[4]}u\n'
    return graph,header

def require_hardware_support(hardware,graph,hls=None):
    hardware=Path(hardware);source=(hardware/'texture_integer_source.cpp').read_bytes();digest=hashlib.sha256(source).hexdigest()
    proof=json.loads((hardware/'candidate_preflight.json').read_text(encoding='utf8'))
    if proof['source_sha256']!=digest:raise ValueError('Implemented HLS source differs from physical preflight')
    if hls is not None and hashlib.sha256((Path(hls)/'src/texture_integer.cpp').read_bytes()).hexdigest()!=digest:
        raise ValueError('Supplied HLS differs from implemented hardware')
    if graph.get('input_roi') and (b'h[26]==0x19600001u' not in source or b'result[10]=view_x' not in source):
        raise ValueError('ROI profile requires ROI-capable implemented hardware')
    return dict(implemented_hls_source_sha256=digest,roi_profile=bool(graph.get('input_roi')))
