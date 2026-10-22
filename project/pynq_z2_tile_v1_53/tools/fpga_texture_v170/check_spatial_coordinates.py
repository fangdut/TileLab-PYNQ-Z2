"""Bind the specialized3x3 coordinate ROM to actual binary model descriptors."""
from pathlib import Path
import argparse,hashlib,json,re,struct,zlib
def inspect(source,profile):
    code=Path(source).read_text()
    if 'spatial_tap_xy' not in code:return None
    if 'static const int SPATIAL_3X3_IC_LIMIT=8;' not in code or 'if(!nearest&&!depth&&k==3&&ic>SPATIAL_3X3_IC_LIMIT)return false;' not in code:
        raise ValueError('Spatial specialization lacks its runtime model guard')
    if 'int ib=(depth||k==3)?0:tap;' not in code or 'xy.range(3,2)' not in code or 'xy.range(1,0)' not in code:
        raise ValueError('Unsupported spatial coordinate mapping')
    match=re.search(r'spatial_xy\[16\]=\{([^}]+)\}',code)
    if not match:raise ValueError('Spatial ROM missing')
    table=[int(x) for x in match[1].split(',')]
    if table!=[0,1,2,4,5,6,8,9,10]+[0]*7:raise ValueError('Spatial ROM differs from3x3 raster order')
    profile=Path(profile);graph=json.loads((profile/'graph.json').read_text());blob=(profile/'model.bin').read_bytes()
    digest=hashlib.sha256(blob).hexdigest()
    if graph['sha256']!=digest or graph['crc32']!=zlib.crc32(blob):raise ValueError('Model provenance mismatch')
    header=struct.unpack_from('<64I',blob)
    if header[0]!=0x17000001 or header[2]!=len(graph['tasks']):raise ValueError('Binary model task count differs')
    standard=[];depth=[]
    for index,t in enumerate(graph['tasks']):
        if list(struct.unpack_from('<24I',blob,(64+index*24)*4))!=t:raise ValueError('Graph and binary task descriptors differ')
        if t[0]==1 and t[11]==3:
            if not 1<=t[9]<=8:raise ValueError('Spatial ROM rejects standard3x3 input channels above8')
            standard.append(dict(step=index+1,input_channels=t[9],output_channels=t[10]))
        if t[0]==2 and t[11]==3:depth.append(index+1)
    for tap in range(9):
        if table[tap]>>2!=tap//3 or table[tap]&3!=tap%3:raise ValueError('Coordinate ROM mismatch')
    return dict(scope='MODEL_BOUND_SPATIAL_COORDINATE_PROOF_NOT_RTL_OR_FPS',passed=True,
                source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),model_sha256=digest,
                binary_descriptors_checked=header[2],standard3x3_layers=standard,depthwise3x3_steps=depth,
                standard3x3_input_channel_limit=8,all_nine_kernel_positions_exact=True,
                unsupported_standard3x3_has_runtime_error_guard=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['source','profile','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=inspect(a.source,a.profile)
    if r is None:raise ValueError('Source does not use spatial ROM')
    if a.out.exists():raise ValueError('Fresh proof required')
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
