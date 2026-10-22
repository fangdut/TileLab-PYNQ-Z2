"""Check row-batch buffer bounds and count MAC iterations; never estimate FPS."""
import argparse, hashlib, json, math
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for name in ['graph','source','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();tasks=json.loads(a.graph.read_text())['tasks'];records=[]
    for index,t in enumerate(tasks):
        if not(t[0]==1 and t[11:14]==[1,1,0] and t[10]>16):continue
        ih,iw,ic,oc=t[7:11];groups=math.ceil(ic/16)
        tile=max(1,min(8192//(groups*iw),ih,16));batches=[];coverage=[]
        for base in range(0,ih,tile):
            active=min(tile,ih-base);local=0
            while local<active:
                shift=0
                for candidate in range(1,5):
                    size=1<<candidate
                    if active-local>=size and iw<=224//size and groups*iw<=2048//size:shift=candidate
                size=1<<shift;width=iw*size
                assert width<=224 and groups*width<=2048
                # These are precisely the contiguous cache/output row addresses.
                for cg in range(groups):
                    first=(cg*active+local)*iw
                    assert 0<=first and first+width<=groups*active*iw<=8192
                    assert first+width<=(cg+1)*active*iw
                coverage.extend(range(base+local,base+local+size))
                batches.append(dict(first_row=base+local,rows=size,packed_width=width))
                local+=size
        assert coverage==list(range(ih))
        blocks=math.ceil(oc/16);taps=math.ceil(ic/8)
        old=ih*math.ceil(iw/32)*32*taps*blocks
        new=sum(math.ceil(b['packed_width']/32)*32*taps*blocks for b in batches)
        records.append(dict(task=index+1,height=ih,width=iw,input_channels=ic,output_channels=oc,
            rows_per_tile=tile,batches=batches,old_mac_iterations=old,new_mac_iterations=new))
    report=dict(scope='STATIC_SCHEDULE_BUFFER_PROOF_NOT_FPGA_SPEED',
        source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),tasks=records,
        old_mac_iterations=sum(r['old_mac_iterations'] for r in records),
        new_mac_iterations=sum(r['new_mac_iterations'] for r in records),
        all_rows_covered_once=True,line_cache_and_quant_buffers_in_bounds=True,
        warning='Excludes DDR, pipeline fill/drain, control and other layers; no FPS inference')
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='tasks'}))

if __name__=='__main__':main()
