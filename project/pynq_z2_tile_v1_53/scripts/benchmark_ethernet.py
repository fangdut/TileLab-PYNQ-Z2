"""Actual board-frame benchmark, never substitute negotiated link rate.

Stop the workstation receiver before running (one board TCP client).
Alarm/manual events are persisted in the usual archive before ACK; preview
frames are validated then ACKed. No reference vision algorithm runs on ARM.
"""
import argparse,hashlib,json,statistics,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,FRAME_BYTES
from workstation import Bridge,Records

def percentile(xs,p):
    return sorted(xs)[min(len(xs)-1,int((len(xs)-1)*p))]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--address',default='169.254.200.10')
    ap.add_argument('--label',required=True);ap.add_argument('--frames',type=int,default=24)
    ap.add_argument('--warmup',type=int,default=3);args=ap.parse_args()
    if not 3<=args.frames<=300 or not 0<=args.warmup<=10:ap.error('frames 3..300, warmup 0..10')
    out=R/'reports/ethernet_20260926';out.mkdir(exist_ok=True)
    if not args.label.replace('_','').isalnum():ap.error('label: letters, digits, underscore only')
    target=out/(args.label+'.json');client=EventTCP(args.address);records=Records(R)
    result=dict(kind='REAL_BOARD_FRAME_TCP',address=args.address,payload_bytes=FRAME_BYTES,
                label=args.label,frames=[],passed=False)
    try:
        for index in range(args.frames+args.warmup):
            start=time.perf_counter();raw,d,m,elapsed=client.capture(36);timing=dict(client.last_timing)
            f,image,mask=Bridge.decode_event(raw,d,m,elapsed)
            decoded=time.perf_counter()
            if f['event_reason'] in (1,2):records.save(f,image,mask,'network_benchmark_event')
            persisted=time.perf_counter();client.ack(f['boot_id'],f['event_id']);end=time.perf_counter()
            row=dict(index=index,warmup=index<args.warmup,frame_id=f['frame_id'],event_id=f['event_id'],boot_id=f['boot_id'],
                     raw_sha256=hashlib.sha256(raw).hexdigest(),metadata=m,descriptor=d,
                     integrity='PASS',**timing,decode_png_ms=(decoded-start)*1000-timing['request_ms'],
                     persist_ms=(persisted-decoded)*1000,cycle_ms=(end-start)*1000)
            result['frames'].append(row);target.write_text(json.dumps(result,indent=2))
            print(json.dumps({k:row[k] for k in ('index','frame_id','request_ms','payload_MB_s','cycle_ms')}),flush=True)
        rows=[r for r in result['frames'] if not r['warmup']]
        result['summary']={k:dict(median=statistics.median(r[k] for r in rows),p95=percentile([r[k] for r in rows],.95),minimum=min(r[k] for r in rows),maximum=max(r[k] for r in rows)) for k in ('request_ms','goodput_MB_s','payload_MB_s','cycle_ms','decode_png_ms')}
        first,last=result['frames'][0]['metadata'],result['frames'][-1]['metadata']
        result['board_deltas']={name:last[i]-first[i] for name,i in [('captured',9),('invalid',10),('gaps',17),('dropped',8),('ack_errors',23)]}
        result['passed']=True
    except Exception as e:
        result['error']=repr(e);raise
    finally:
        target.write_text(json.dumps(result,indent=2));client.close();records.db.close()
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__':main()
