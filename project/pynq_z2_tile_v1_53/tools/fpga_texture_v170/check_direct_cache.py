"""Prove direct PW cache and physical line bounds for the frozen binary graph."""
from pathlib import Path
import argparse,hashlib,json,struct

def analyze(tasks):
    rows=[]
    for i,t in enumerate(tasks):
        if t[0] not in (1,2):continue
        ih,iw,ic,oc,k,st,pad=t[7:14]
        if not (1<=iw<=224 and ih>0 and ic>0 and oc>0 and k in (1,3) and st in (1,2) and pad in (0,1)):raise ValueError('Unsupported convolution geometry')
        oh=(ih+2*pad-k)//st+1;ow=(iw+2*pad-k)//st+1
        if not (1<=ow<=224 and oh>=1):raise ValueError('Quantization row capacity exceeded')
        cached=t[0]==1 and k==1 and st==1 and pad==0
        groups=(ic+15)//16
        if t[0]==1 and not cached and not ((k==3 and ic==3) or (k==1 and ic<=48)):raise ValueError('Uncached ordinary convolution exceeds three physical row banks')
        r=dict(task=i+1,cached=cached,input_width=iw,input_channels=ic)
        if cached:
            tile=max(1,min(8192//(groups*iw),max(1,min(oh,16))))
            peak=0;covered=0
            for ybase in range(0,oh,tile):
                active=min(oh-ybase,tile);local=0
                while local<active:
                    shift=0
                    for s in (1,2,3,4):
                        if active-local>=1<<s and iw<=224//(1<<s) and groups*iw<=2048//(1<<s):shift=s
                    batch=1<<shift;packed_width=iw*batch
                    last=(groups-1)*active*iw+local*iw+packed_width-1
                    if packed_width>224 or last>=8192:raise ValueError('Direct PW cache or quantization row exceeds storage')
                    peak=max(peak,last);covered+=batch;local+=batch
            if covered!=oh:raise ValueError('PW row coverage differs')
            r.update(max_cache_word=peak,output_rows_covered=covered)
        else:r.update(physical_row_banks=3,max_line_column=iw-1)
        rows.append(r)
    return rows

def inspect(source,profile):
    if b'Single-read physical row banks' not in source.read_bytes():return None
    data=(profile/'model.bin').read_bytes();header=struct.unpack_from('<64I',data);graph=json.loads((profile/'graph.json').read_text())
    tasks=[list(struct.unpack_from('<24I',data,256+i*96)) for i in range(header[2])]
    if tasks!=graph['tasks']:raise ValueError('Graph JSON differs from binary task descriptors')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    rows=analyze(tasks)
    return dict(scope='STATIC_BINARY_GRAPH_BUFFER_BOUNDS_NOT_RUNTIME_INFERENCE',source_sha256=sha(source),model_sha256=sha(profile/'model.bin'),model_tasks=len(tasks),convolution_tasks=len(rows),cached_pw_tasks=sum(r['cached'] for r in rows),max_direct_cache_word=max(r.get('max_cache_word',0) for r in rows),cache_capacity_words=8192,line_banks=3,line_words_per_bank=512,quantization_row_words=224,tasks=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inspect(a.source,a.profile)
    if r is None:raise ValueError('Source is not the direct-cache kernel')
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='tasks'}))
if __name__=='__main__':main()
