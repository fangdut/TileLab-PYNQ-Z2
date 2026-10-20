"""Export fused CNN, PCA and normal codebook as a sealed PL graph blob."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,zlib
import numpy as np
from prepare_model import folded_network,sha,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--model',type=Path,required=True);a=p.parse_args()
    net=folded_network(a.weights);compression=np.load(a.model/'compression.npz',allow_pickle=False)
    record=json.loads((a.model/'model.json').read_text(encoding='utf8'))
    header=np.zeros(64+96*16,dtype='<u4');chunks=[];cursor=len(header);ops=[];shapes=[(3,448,448)]
    def data(value):
        nonlocal cursor
        value=np.asarray(value,dtype='<f4').ravel().view('<u4');offset=cursor;cursor+=len(value);chunks.append(value);return offset
    def node(kind,inputs,shape,**kw):
        index=len(shapes);shapes.append(shape);ops.append(dict(op=kind,inputs=inputs,output=index,**kw));return index
    def conv(source,module,relu):
        c,h,w=shapes[source];k=module.kernel_size[0];s=module.stride[0];pad=module.padding[0];out=module.out_channels
        assert module.groups==1 and module.dilation==(1,1) and out%4==0
        assert (c*k*w+3)//4+c*k*k<=28672
        return node(1,[source],(out,(h+2*pad-k)//s+1,(w+2*pad-k)//s+1),weight=data(module.weight.detach().numpy()),bias=data(module.bias.detach().numpy()),kernel=k,stride=s,pad=pad,relu=int(relu))
    def pool(source,op,stride):
        c,h,w=shapes[source];return node(op,[source],(c,(h-1)//stride+1,(w-1)//stride+1),stride=stride)
    current=pool(conv(0,net.conv1,True),2,2)
    feature_a=None
    for stage_index,stage in enumerate([net.layer1,net.layer2,net.layer3],1):
        for block in stage:
            skip=current;x=conv(current,block.conv1,True);x=conv(x,block.conv2,True);x=conv(x,block.conv3,False)
            if block.downsample is not None:skip=conv(skip,block.downsample[0],False)
            assert shapes[skip]==shapes[x]
            current=node(3,[x,skip],shapes[x])
        if stage_index==2:feature_a=current
    fa=pool(feature_a,4,1);fb=pool(current,4,1)
    assert shapes[fa]==(512,56,56) and shapes[fb]==(1024,28,28) and len(ops)<=96
    # A liveness allocator prevents the residual network from requiring the
    # sum of all intermediate tensors in DDR. Output allocation precedes frees.
    uses=Counter(i for op in ops for i in op['inputs']);uses[fa]+=1;uses[fb]+=1
    sizes=[int(np.prod(s)) for s in shapes];offsets={0:0};free=[];high=sizes[0]
    def allocate(size):
        nonlocal high
        size=(size+15)//16*16
        for i,(offset,length) in enumerate(free):
            if length>=size:
                free.pop(i)
                if length>size:free.append((offset+size,length-size))
                return offset
        offset=high;high+=size;return offset
    def release(offset,length):
        free.append((offset,(length+15)//16*16));free.sort();merged=[]
        for start,size in free:
            if merged and merged[-1][0]+merged[-1][1]==start:merged[-1]=(merged[-1][0],merged[-1][1]+size)
            else:merged.append((start,size))
        free[:]=merged
    tasks=[]
    for op in ops:
        src=op['inputs'][0];dst=op['output'];offsets[dst]=allocate(sizes[dst]);c,h,w=shapes[src]
        t=[0]*16;t[:3]=[op['op'],offsets[src],offsets[dst]]
        if op['op']==1:t[3:13]=[op['weight'],op['bias'],h,w,c,shapes[dst][0],op['kernel'],op['stride'],op['pad'],op['relu']]
        elif op['op'] in (2,4):t[5:12]=[h,w,c,0,3,op['stride'],1]
        else:t[3]=offsets[op['inputs'][1]];t[5]=sizes[src]
        tasks.append(t)
        for inp in op['inputs']:
            uses[inp]-=1
            if uses[inp]==0:release(offsets[inp],sizes[inp])
    projected=allocate(56*56*64);raw=allocate(56*56);smooth=allocate(56*56)
    projection=data(compression['projection'].T);mean=data(compression['mean']);centers=data(compression['centers'])
    assert cursor*4<128*1024*1024 and high*4<128*1024*1024
    header[:22]=[0x16900001,cursor,len(tasks),448,56,64,1024,0,projected,raw,smooth,offsets[fa],offsets[fb],projection,mean,centers,np.float32(record['threshold']).view(np.uint32),high,28672,4,512,1024]
    for i,t in enumerate(tasks):header[64+i*16:80+i*16]=t
    blob=np.concatenate([header]+chunks).astype('<u4');blob.tofile(a.model/'model.bin')
    metadata=dict(version='V169_FULL_PL_GRAPH',model_bytes=blob.nbytes,model_words=cursor,workspace_words=high,workspace_bytes=high*4,steps=len(tasks),
        sha256=sha(a.model/'model.bin'),crc32=zlib.crc32(blob.tobytes()),threshold=float(np.float32(record['threshold'])),
        pl_computes=['resize','normalize','all CNN convolutions','residual additions','pooling','PCA projection','nearest normal search','smoothing','image alarm','pixel mask'],
        ps_computes=['TCP transport','CRC checks','cache ownership','start/poll accelerator'],pc_computes=['file decode and RGB packing','transport','display','save evidence'],
        tasks=tasks,graph=ops,tensor_shapes=shapes,tensor_offsets=offsets,
        model_derived_data_license='CC BY-NC-SA 4.0; pretrained weights keep upstream terms',
        deployment_verified=False)
    save(a.model/'graph.json',metadata)
    print(json.dumps({k:metadata[k] for k in ['model_bytes','workspace_bytes','steps','sha256','crc32','threshold']}),flush=True)

if __name__=='__main__':main()
