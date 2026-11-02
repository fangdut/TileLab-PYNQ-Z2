"""Pack the integer graph and bank into the hardware ABI (no host inference)."""
from pathlib import Path
from collections import Counter
import argparse,json,zlib
import numpy as np
import torch
from evaluate_lightweight import save,sha

def export(folder, graph, head, side, threshold=None):
    header=np.zeros(64+96*24,dtype='<u4'); chunks=[]; cursor=header.nbytes//8
    def u64(values):
        nonlocal cursor
        v=np.asarray(values,dtype='<u8').ravel(); off=cursor; chunks.append(v);cursor+=len(v);return off
    def u32(values):
        v=np.asarray(values,dtype='<u4').ravel()
        if len(v)%2:v=np.pad(v,(0,1))
        return u64(v.view('<u8'))*2
    shapes=[(3,side,side)]; nodes=graph['nodes']; quant=graph['quant']; offsets={0:0}; sizes=[side*side];high=side*side
    uses=Counter(s for n in nodes for s in n['inputs']);uses[graph['fa']]+=1;uses[graph['fb']]+=1;free=[];tasks=[]
    def alloc(size):
        nonlocal high
        for i,(off,n) in enumerate(free):
            if n>=size:
                free.pop(i)
                if n>size:free.append((off+size,n-size))
                return off
        off=high;high+=size;return off
    def release(off,n):
        free.append((off,n));free.sort();merged=[]
        for start,length in free:
            if merged and merged[-1][0]+merged[-1][1]==start:merged[-1]=(merged[-1][0],merged[-1][1]+length)
            else:merged.append((start,length))
        free[:]=merged
    for i,n in enumerate(nodes,1):
        src=n['inputs'][0];ic,ih,iw=shapes[src];t=[0]*24;t[1]=offsets[src]
        if n['kind']=='conv':
            q=quant[i];w=q['weight'].numpy().astype('i1');oc=w.shape[0];k=w.shape[2];s=n['stride'];p=n['pad']
            # Exhaustive input-independent bound: any signed8 activation is
            # safe in the signed24 requant input, including quantized bias.
            bound=127*np.abs(w.astype('i8')).reshape(oc,-1).sum(1)+np.abs(q['bias'].numpy().astype('i8'))
            active=q['multiplier'].numpy()!=0
            # Some folded dead channels have tiny scales and a zero integer
            # multiplier. Their requantized output is identically zero even
            # if the unused accumulator wraps; prove the active channels.
            if active.any() and int(bound[active].max())>=(1<<23):raise ValueError('Signed24 active-accumulator proof failed')
            oh=(ih+2*p-k)//s+1;ow=(iw+2*p-k)//s+1;depth=n.get('groups',1)==ic and ic>1
            if n.get('groups',1) not in (1,ic):raise ValueError('Unsupported groups')
            if depth:
                packed=np.zeros(((oc+15)//16,k*k,16),dtype='i1')
                for o in range(oc):packed[o//16,:,o%16]=w[o,0].ravel()
            else:
                taps=((ic+7)//8)*k*k;packed=np.zeros(((oc+15)//16,taps,16,8),dtype='i1')
                for o in range(oc):
                    for c in range(ic):
                        for r in range(k):
                            for col in range(k):packed[o//16,(c//8*k+r)*k+col,o%16,c%8]=w[o,c,r,col]
            wo=u64(packed.ravel().view('<u8'))
            bo=u32(q['bias'].numpy().view('<u4'));m=q['multiplier'].numpy()
            if np.any(m<0) or np.any(m>=(1<<27)):raise ValueError('Requantization multiplier exceeds exact 27-bit hardware bound')
            mo=u32(m.astype('<u4'));relu=2 if n.get('relu6') else int(n['relu'])
            qmax=min(127,int(np.floor(6/graph['scales'][i]+.5))) if relu==2 else 127
            t[0]=2 if depth else 1;t[4:16]=[wo,bo,mo,ih,iw,ic,oc,k,s,p,relu,qmax]
        elif n['kind']=='add':
            oc,oh,ow=ic,ih,iw;t[0]=3;t[3]=offsets[n['inputs'][1]];t[4:6]=quant[i]['multipliers'];t[7]=sizes[src]
        else:raise ValueError('Unsupported op '+n['kind'])
        shapes.append((oc,oh,ow));size=((oc+15)//16)*oh*ow;sizes.append(size);offsets[i]=alloc(size);t[2]=offsets[i];tasks.append(t)
        for s in n['inputs']:
            uses[s]-=1
            if uses[s]==0:release(offsets[s],sizes[s])
    projection=np.asarray(head['projection'],dtype='<i2');bias=np.asarray(head['bias'],dtype='<i8')
    pram=np.zeros((128,16),dtype='<u8')
    for k in range(128):
        for o in range(64):
            idx=o*8+k//16
            pram[idx//4,k%16]|=np.uint64(np.uint16(projection[k,o]))<<np.uint64((idx%4)*16)
    po=u64(pram);pb=u64(bias.view('<u8'))
    centers=np.asarray(head['centers'],dtype='<i2');nram=np.zeros((1024,16),dtype='<u8')
    for n in range(len(centers)):
        for k in range(64):nram[n,k%16]|=np.uint64(np.uint16(centers[n,k]))<<np.uint64((k//16)*16)
    co=u64(nram);im=u64(np.asarray(head['input_m'],dtype='<i8').view('<u8'));ib=u64(np.asarray(head['input_b'],dtype='<i8').view('<u8'))
    grid=side//8;projected=alloc(grid*grid*8)
    h=[0x17000001,cursor*8,len(tasks),side,grid,64,len(centers),offsets[graph['fa']],offsets[graph['fb']],32,96,
       po,pb,co,int(head['shift']),int(head['threshold']) if threshold is None else threshold,high*16,im,ib,projected]
    header[:len(h)]=h
    for i,t in enumerate(tasks):header[64+i*24:88+i*24]=t
    blob=np.concatenate([header.view('<u8')]+chunks).astype('<u8');blob.tofile(folder/'model.bin')
    metadata=dict(version='V170_INT8_FULL_PL_GRAPH',model_bytes=blob.nbytes,sha256=sha(folder/'model.bin'),crc32=zlib.crc32(blob.tobytes()),
        workspace_bytes=high*16,steps=len(tasks),side=side,grid=grid,threshold=h[15],tasks=tasks,shapes=shapes,
        model_derived_data_license='CC BY-NC-SA 4.0',board_verified=False)
    save(folder/'graph.json',metadata);return metadata

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);a=p.parse_args()
    graph=torch.load(a.profile/'quantized_graph.pt',weights_only=False,map_location='cpu')
    head=np.load(a.profile/'integer_head.npz',allow_pickle=False)
    print(json.dumps(export(a.profile,graph,head,graph['side'])),flush=True)
if __name__=='__main__':main()
