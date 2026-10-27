"""Seal the frame-engine ABI; no runtime CPU inference or silent image resize."""
from pathlib import Path
import argparse,copy,json,struct,hashlib,zlib
import numpy as np

KINDS={'conv2d_int16_mac48':2,'dynamic_integer_instance_norm':3,'relu_requant16':4,'max_pool_2x2_stride2':5,'bilinear_2x_quarter_weights':6,'residual_add_requant16':7,'channel_concat_requant16':8,'logit_greater_than_zero':9}
def align(n,a=64):return (n+a-1)//a*a
def scalar(t):
    if isinstance(t['exponent'],list):raise ValueError('Scalar activation scale required')
    return t['exponent']
def assemble(program_dir,out,width,height,retain=False,synthetic=False):
    out.mkdir(exist_ok=False);original=json.loads((program_dir/'operator_program.json').read_text());p=copy.deepcopy(original)
    if width%16 or height%16 or not 16<=width<=256 or not 16<=height<=1408 or width*height>360448:raise ValueError('Supported geometry: multiples16, at most256x1408')
    tensors=p['tensors'];ops=p['operators'];n=len(tensors);last={t['id']:-1 for t in tensors}
    for i,op in enumerate(ops):
        for source in op['input_tensors']:last[source]=i
    last[p['output_tensor']]=len(ops)
    for t in tensors:
        t['shape'][2]=t['shape'][2]*height//1408;t['shape'][3]=t['shape'][3]*width//256
    free=[];live={};end=0;peak=0
    def allocate(t):
        nonlocal end,peak
        size=align(int(np.prod(t['shape']))*2);free.sort()
        for j,(start,available) in enumerate(free):
            if available>=size:
                del free[j]
                if available>size:free.append((start+size,available-size))
                break
        else:start=end;end+=size
        live[t['id']]=(start,size);t['offset16']=start//2;peak=max(peak,sum(s for _,s in live.values()))
    def release(i):
        if retain:return
        for ident in list(live):
            if last[ident]<=i:free.append(live.pop(ident))
        free.sort();merged=[]
        for start,size in free:
            if merged and merged[-1][0]+merged[-1][1]==start:merged[-1]=(merged[-1][0],merged[-1][1]+size)
            else:merged.append((start,size))
        free[:]=merged
    allocate(tensors[p['input_tensor']])
    for i,op in enumerate(ops):allocate(tensors[op['output_tensor']]);release(i)
    if end>134217728:raise ValueError('Tensor arena exceeds128MiB')
    # A live overlap audit is independent of the first-fit allocator.
    active={p['input_tensor']}
    for i,op in enumerate(ops):
        active.add(op['output_tensor']);ranges=sorted((tensors[k]['offset16']*2,tensors[k]['offset16']*2+align(int(np.prod(tensors[k]['shape']))*2),k) for k in active)
        assert all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),(i,ranges)
        active={k for k in active if retain or last[k]>i}
    header=[0]*64;toff=64;ooff=toff+n*16;blob=bytearray((ooff+len(ops)*32)*4)
    def append(raw):
        blob.extend(b'\0'*(align(len(blob))-len(blob)));start=len(blob);blob.extend(raw);return start
    weight_source=(program_dir/'weights_int16.bin').read_bytes();rng=np.random.default_rng(198);gold_weights={};descriptors=[];normalization={}
    for i,op in enumerate(ops):
        dst=tensors[op['output_tensor']];src=tensors[op['input_tensors'][0]];kind=KINDS[op['kind']]
        d=[0]*32;d[0]=kind;d[1]=src['id'];d[2]=op['input_tensors'][1] if len(op['input_tensors'])>1 else 0;d[3]=dst['id']
        if kind==2:
            weights=np.frombuffer(weight_source,dtype='<i2',count=op['weights_bytes']//2,offset=op['weights_offset']).copy().reshape(op['weights_shape'])
            if synthetic and op['groups']==1:
                weights=rng.integers(-12000,12001,weights.shape,dtype='i2')
                if dst['shape'][1]==1:weights=np.abs(weights)
            gold_weights[op['name']]=weights
            cin=src['shape'][1];cout=dst['shape'][1];kh,kw=weights.shape[2:];terms=(cin//op['groups'])*kh*kw;stride=align(terms*2,8)//2
            if op['groups']==3:
                expected=np.tile(np.array([2,1,0,-1,-2],dtype='i2'),(3,1,5,1));assert np.array_equal(weights,expected)
                assert scalar(src)==0 and dst['exponent']==0;d[0]=10
            else:
                assert op['groups']==1 and cout<=32 and cin<=64 and terms<=800
                packed=np.zeros((cout,stride),dtype='<i2');packed[:,:terms]=weights.transpose(0,2,3,1).reshape(cout,terms);d[5]=append(packed.tobytes())//2
                shifts=[int(e)-scalar(src)-int(w) for e,w in zip(dst['exponent'],op['weight_exponents'])]
                assert all(-16<=v<=48 for v in shifts);d[4]=append(struct.pack('<'+'i'*cout,*shifts))//4;d[22]=cout
            d[6:17]=[kh,kw,*op['dilation'],*op['padding'],cin,cout,op['groups'],terms,stride]
        elif kind==3:
            count=dst['shape'][2]*dst['shape'][3];exp=scalar(dst);params=[];sx=src['exponent'];gamma=op['gamma_q30'];beta=op['beta_q30']
            if synthetic:
                gamma=[int(rng.choice([.75,.875,1.,1.125,1.25])*2**30) for _ in gamma];beta=[int(rng.choice([-.25,-.125,0,.125,.25])*2**30) for _ in beta]
            for c in range(dst['shape'][1]):
                eps=int(round(1e-5*count*count*2.0**(-2*(sx[c] if isinstance(sx,list) else sx))));params += [count,0,0,eps&((1<<64)-1),eps>>64,gamma[c]&((1<<64)-1),beta[c]&((1<<64)-1),exp&((1<<64)-1)]
            d[4]=append(struct.pack('<'+'Q'*len(params),*params))//4;d[22]=len(params)*2;normalization[op['name']]=dict(gamma_q30=gamma,beta_q30=beta)
        elif kind in [4,6]:d[19]=scalar(dst)-scalar(src)+(4 if kind==6 else 0)
        elif kind==7:
            other=tensors[d[2]];minimum=min(scalar(src),scalar(other));d[19]=scalar(src)-minimum;d[20]=scalar(other)-minimum;d[21]=scalar(dst)-minimum
        elif kind==8:d[19]=scalar(dst)-scalar(src);d[20]=scalar(dst)-scalar(tensors[d[2]])
        descriptors.append(d)
    for t in tensors:
        words=[0]*16;_,c,h,w=t['shape'];words[:9]=[t['offset16'],c,h,w,int(isinstance(t['exponent'],list)),scalar(t) if not isinstance(t['exponent'],list) else 0,0,c*h*w,last[t['id']]]
        struct.pack_into('<16I',blob,(toff+t['id']*16)*4,*[int(v)&0xffffffff for v in words])
    for i,d in enumerate(descriptors):struct.pack_into('<32I',blob,(ooff+i*32)*4,*[int(v)&0xffffffff for v in d])
    blob.extend(b'\0'*(align(len(blob),8)-len(blob)));header[0]=0x17000001;header[1]=len(blob);header[2]=len(ops);header[4]=1;header[16]=align(end);header[17]=n;header[18]=toff;header[19]=ooff;header[27]=0x19800001;header[28]=width;header[29]=height;header[30]=p['input_tensor'];header[31]=p['output_tensor'];header[32]=len(blob)//4;header[33]=32;header[34]=16
    struct.pack_into('<64I',blob,0,*header);(out/'model.bin').write_bytes(blob)
    metadata=dict(format='TILELAB_HFENET_198_ABI1',kernel_kind='HFENET198',pl_identity=0x19800001,sha256=hashlib.sha256(blob).hexdigest(),crc32=zlib.crc32(blob),model_bytes=len(blob),grid=1,steps=len(ops),workspace_bytes=header[16],width=width,height=height,threshold=0,tensor_count=n,retained_fixture=retain,synthetic_weights=synthetic,source_program_sha256=hashlib.sha256((program_dir/'operator_program.json').read_bytes()).hexdigest(),allocation_peak_live_bytes=peak,full_hardware_verified=False)
    (out/'graph.json').write_text(json.dumps(metadata,indent=2),encoding='utf8');(out/'allocation.json').write_text(json.dumps(dict(tensors=tensors,last_use=last,arena_bytes=end,peak_live_bytes=peak),indent=2),encoding='utf8')
    (out/'gold_metadata.json').write_text(json.dumps(dict(normalization=normalization,source=p),indent=2),encoding='utf8');np.savez_compressed(out/'gold_weights.npz',**gold_weights)
    print(json.dumps(metadata));return metadata
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--program',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,default=256);p.add_argument('--height',type=int,default=1408);p.add_argument('--retain',action='store_true');p.add_argument('--synthetic',action='store_true');a=p.parse_args();assemble(a.program,a.out,a.width,a.height,a.retain,a.synthetic)
