"""HFENet198 model identity; deliberately incompatible with the legacy kernel."""
from pathlib import Path
import hashlib,json,struct,zlib

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_identity(profile):
    profile=Path(profile);g=json.loads((profile/'graph.json').read_text());b=(profile/'model.bin').read_bytes()
    if len(b)<256:raise ValueError('Truncated model')
    h=struct.unpack_from('<64I',b)
    expected=dict(kernel_kind='HFENET198',pl_identity=0x19800001,sha256=hashlib.sha256(b).hexdigest(),crc32=zlib.crc32(b),model_bytes=len(b),grid=h[4],steps=h[2],workspace_bytes=h[16],width=h[28],height=h[29],tensor_count=h[17])
    if any(g.get(k)!=v for k,v in expected.items()):raise ValueError('Model metadata does not describe actual bytes')
    if (h[0],h[1],h[2],h[4],h[17],h[27],h[28],h[29],h[33],h[34])!=(0x17000001,len(b),71,1,72,0x19800001,256,1408,32,16):raise ValueError('Wrong final model ABI or geometry')
    if not 0<h[16]<=134217728 or len(b)>2097152 or g['synthetic_weights'] or g['retained_fixture']:raise ValueError('Only the production lifetime-allocated model may be loaded')
    header='\n'.join(f'#define {k} {v}u' for k,v in dict(MODEL_BYTES=len(b),MODEL_CRC=expected['crc32'],MODEL_GRID=1,MODEL_WIDTH=256,MODEL_HEIGHT=1408,MODEL_WORK_BYTES=h[16]).items())+'\n'
    return g,header

def require_hardware_support(hw,g,hls):
    hw=Path(hw);hls=Path(hls);p=json.loads((hw/'candidate_preflight.json').read_text())
    if p['identity']!=0x19800001 or p['model_sha256']!=g['sha256']:raise ValueError('Candidate/model identity mismatch')
    for name,value in p['source_components'].items():
        saved=hw/('texture_integer_source.cpp' if name=='texture_integer.cpp' else name)
        if sha(saved)!=value or sha(hls/'src'/name)!=value:raise ValueError('Implemented source/header mismatch: '+name)
    return dict(identity=0x19800001,model_sha256=g['sha256'],source_components=p['source_components'],geometry=[256,1408],cpu_detection=False)
