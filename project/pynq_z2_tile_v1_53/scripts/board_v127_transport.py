"""Real same-event comparison: RAW32, old adaptive RLE, new adaptive packing."""
from pathlib import Path
import sys,time,json,hashlib,socket,struct,statistics
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
from board_v18_continuous import action,state,wait_idle,read_player
O=R/'reports/v132';O.mkdir(exist_ok=True)

def run():
 wait_idle();c=EventTCP('169.254.200.10');rows=[]
 def empty(threshold=90):
  action('display',value='station_6');time.sleep(.4)
  while c.stats()['depth']:
   _,d,m,_=c.capture(threshold,passes=4);c.ack(m[2],d[0])
  c.configure(threshold,passes=4);time.sleep(.3)
  _,d,m,_=c.capture(threshold,passes=4);c.ack(m[2],d[0])
  assert ((d[7]>>8)&255)==threshold and d[7]&(1<<25)
 try:
  empty();before=c.stats();assert before['version']==0x11b00
  for source in ('station_6','station_1','real_000','real_005','transport_noise'):
   threshold=255 if source=='transport_noise' else 90
   empty(threshold);action('display',value=source);time.sleep(.5)
   _,d,m,_=c.capture(threshold,passes=4);c.ack(m[2],d[0])
   for sample in range(10):
    values={};timings={};descs={};order=['raw','legacy','compact'];order=order[sample%3:]+order[:sample%3]
    for mode in order:
     c.compression=mode!='raw';c.packed=mode=='compact'
     raw,d,m,_=c.capture(threshold,passes=4)
     assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
     values[mode]=raw;descs[mode]=d;timings[mode]=dict(c.last_timing)
    assert values['raw']==values['legacy']==values['compact'],'Canonical image bytes changed'
    assert descs['raw']==descs['legacy']==descs['compact'],'Event descriptor changed'
    assert len({t['pixel_crc32'] for t in timings.values()})==1
    c.ack(m[2],d[0]);rows.append(dict(source=source,sample=sample,event=d[0],frame=d[2],sha256=hashlib.sha256(raw).hexdigest(),exact=True,**timings))
   print(json.dumps(dict(source=source,**{mode:statistics.median(r[mode]['request_ms'] for r in rows if r['source']==source) for mode in ('raw','legacy','compact')})),flush=True)
  # Explicitly request PACK25 then abort the real packed payload before ACK.
  c.compression=True;c.packed=True
  raw,d,m,_=c.capture(255,passes=4);assert c.last_timing['wire_codec']=='BGR24_MASK1'
  head=c.stats()['head'];c.close();time.sleep(.08)
  sock=socket.create_connection(('169.254.200.10',9133),timeout=3);sock.sendall(struct.pack('<4I',MAGIC,1,255,14))
  header=bytearray()
  while len(header)<276:header.extend(sock.recv(276-len(header)))
  assert struct.unpack('<I',header[12:16])[0]==527
  assert sock.recv(1000)
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0));sock.close();time.sleep(.15)
  again,dd,mm,_=c.capture(255,passes=4)
  assert d==dd and raw==again and c.stats()['head']==head
  c.ack(mm[2],dd[0]);assert c.stats()['head']==(head+1)&0xffffffff
  after=c.stats()
  assert after['descriptor_verified_frames']==after['captured'] and after['error_status']==0
  for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert after[k]==before[k],k
  noise=[r for r in rows if r['source']=='transport_noise']
  assert all(r['legacy']['wire_codec']=='RAW32' and r['compact']['wire_codec']=='BGR24_MASK1' and r['compact']['wire_payload_bytes']==2880000 for r in noise)
  assert all(r['compact']['wire_payload_bytes']<=r['legacy']['wire_payload_bytes']<=FRAME_BYTES for r in rows)
  summary={name:dict(samples=10,**{mode:{field:statistics.median(r[mode][field] for r in rows if r['source']==name) for field in ('request_ms','header_wait_ms','payload_ms','wire_payload_bytes','wire_saving_percent','decode_ms','crc_ms')} for mode in ('raw','legacy','compact')}) for name in sorted({r['source'] for r in rows})}
  result=dict(passed=True,byte_exact_triplets=len(rows),packed_reconnect_same_event=True,before=before,after=after,summary=summary,rows=rows)
  (O/'transport_comparison.json').write_text(json.dumps(result,indent=2));print('All 50 same-event three-mode comparisons and packed reconnect passed',flush=True)
 except Exception as e:
  (O/f'transport_failure_{time.time_ns()}.json').write_text(json.dumps(dict(error=str(e),rows=rows,failures=c.failures),indent=2));raise
 finally:action('display',value='station_6');c.close()
if __name__=='__main__':run()
