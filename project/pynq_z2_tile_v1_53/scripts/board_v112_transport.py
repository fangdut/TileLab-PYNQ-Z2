"""Same-event RAW/RLE A/B measurement; compare ALL image/mask bytes.
No candidate algorithm changes and no image classification on ARM or PC.
"""
from pathlib import Path
import sys,time,json,hashlib,socket,struct,statistics
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
from board_v18_continuous import action,state,wait_idle,read_player
OUT=R/'reports/v132';OUT.mkdir(exist_ok=True)

def run():
 wait_idle();c=EventTCP('169.254.200.10');rows=[]
 try:
  action('display',value='station_6')
  deadline=time.monotonic()+8
  while read_player().get('source')!='station_6':
   if time.monotonic()>deadline:raise TimeoutError('HDMI source did not confirm empty scene')
   time.sleep(.1)
  time.sleep(.4)
  while c.stats()['depth']:
   _,d,m,_=c.capture(89);c.ack(m[2],d[0])
  _,d,m,_=c.capture(89);c.ack(m[2],d[0]);before=c.stats();assert before['version']==0x10c00
  for source in ['station_6','station_1','real_000','real_005','transport_noise']:
   threshold=255 if source=='transport_noise' else 89
   action('display',value='station_6');time.sleep(.3)
   while c.stats()['depth']:
    _,d,m,_=c.capture(threshold);c.ack(m[2],d[0])
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    _,d,m,_=c.capture(threshold);c.ack(m[2],d[0])
    if ((d[7]>>8)&255)==threshold:break
   assert ((d[7]>>8)&255)==threshold,'Test threshold did not apply before noise'
   action('display',value=source);time.sleep(.5)
   _,d,m,_=c.capture(threshold);c.ack(m[2],d[0])
   for sample in range(10):
    versions={};timing={};descs={}
    for compressed in ([False,True] if sample%2==0 else [True,False]):
     c.compression=compressed;raw,d,m,_=c.capture(threshold)
     assert c.last_timing['pixel_crc_verified'] and c.last_timing['header_crc_verified'];versions[compressed]=raw;timing[compressed]=dict(c.last_timing);descs[compressed]=d
    if versions[True]!=versions[False] or descs[True]!=descs[False]:
     import numpy as np
     aa=np.frombuffer(versions[False],dtype='<u4');bb=np.frombuffer(versions[True],dtype='<u4');bad=np.flatnonzero(aa!=bb)
     proof=dict(source=source,sample=sample,raw_desc=descs[False],compact_desc=descs[True],mismatch_pixels=len(bad),first_indices=bad[:32].tolist(),raw_values=aa[bad[:32]].tolist(),compact_values=bb[bad[:32]].tolist(),timing=timing)
     stamp=time.time_ns();(OUT/f'pair_mismatch_{stamp}.json').write_text(json.dumps(proof,indent=2))
     for mode in [False,True]:(OUT/f'pair_mismatch_{stamp}_{mode}.bin').write_bytes(versions[mode])
     raise AssertionError('Same event changed pixels/metadata; exact mismatch evidence retained')
    assert timing[True]['pixel_crc32']==timing[False]['pixel_crc32'];c.ack(m[2],d[0]);rows.append(dict(source=source,sample=sample,event=d[0],frame=d[2],sha256=hashlib.sha256(raw).hexdigest(),exact=True,raw=timing[False],compact=timing[True]))
   print(json.dumps(dict(source=source,raw_ms=statistics.median(r['raw']['request_ms'] for r in rows if r['source']==source),compact_ms=statistics.median(r['compact']['request_ms'] for r in rows if r['source']==source),saving=statistics.median(r['compact']['wire_saving_percent'] for r in rows if r['source']==source))),flush=True)
  # Abort mid-payload and then read the same pinned event again.
  action('display',value='station_6');time.sleep(.3)
  for _ in range(3):
   _,d,m,_=c.capture(89);c.ack(m[2],d[0])
  action('display',value='real_000');time.sleep(.5);c.compression=False;raw,d,m,_=c.capture(89);old_event=d[0];head=c.stats()['head'];c.close();time.sleep(.05)
  sock=socket.create_connection(('169.254.200.10',9133),timeout=3);sock.sendall(struct.pack('<4I',MAGIC,1,89,2))
  part=sock.recv(800);assert part
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0));sock.close();time.sleep(.15)
  c.compression=True;again,dd,mm,_=c.capture(89);assert d==dd and raw==again and c.stats()['head']==head
  c.ack(mm[2],dd[0]);assert c.stats()['head']==head+1
  after=c.stats()
  assert after['gaps']==before['gaps'] and after['invalid']==before['invalid'] and after['dropped']==before['dropped'] and after['error_status']==0
  noise=[r for r in rows if r['source']=='transport_noise'];assert all(r['compact']['wire_codec']=='RAW32' for r in noise),'Noise did not exercise fallback'
  assert all(r['compact']['wire_payload_bytes']<=FRAME_BYTES for r in rows)
  assert after['compression_probe_bypasses']-before['compression_probe_bypasses']>=10,'Noise did not use probe bypass'
  summary={s:{'samples':sum(r['source']==s for r in rows),**{k:statistics.median(r[mode][field] for r in rows if r['source']==s) for k,mode,field in [('raw_request_ms','raw','request_ms'),('compact_request_ms','compact','request_ms'),('compact_bytes','compact','wire_payload_bytes'),('saving_percent','compact','wire_saving_percent'),('decode_ms','compact','decode_ms'),('crc_ms','compact','crc_ms')]}} for s in sorted({r['source'] for r in rows})}
  result=dict(passed=True,byte_exact_samples=len(rows),reconnect_same_event=True,before=before,after=after,summary=summary,rows=rows)
  (OUT/'transport_comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
 except Exception as e:
  (OUT/f'transport_failure_{time.time_ns()}.json').write_text(json.dumps(dict(error=str(e),rows=rows,failures=c.failures),indent=2));raise
 finally:action('display',value='station_6');c.close()
if __name__=='__main__':run()
