"""Actual pinned-DDR early/late corruption during overlapping PACK25 replies."""
from pathlib import Path
import sys,time,json,struct,socket,zlib,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/noncanonical';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
from board_v18_continuous import action,wait_idle
from board_v125_noncanonical import patch,exact

def case(index):
 c=EventTCP('169.254.200.10',packed=True);changed=False
 try:
  c.stats();raw,d,m,_=c.capture(255,passes=4);assert c.last_timing['wire_codec']=='BGR24_MASK1'
  slot=d[1];old=struct.unpack_from('<I',raw,index*4)[0];bad=old^(1<<25);boot=m[2];event=d[0];c.close();time.sleep(.15)
  changed=True;patch(boot,event,slot,index,old,bad,f'inject_{index}')
  partial=bytearray()
  with socket.create_connection(('169.254.200.10',9133),timeout=3) as s:
   s.sendall(struct.pack('<4I',MAGIC,1,255,14))
   while True:
    try:b=s.recv(65536)
    except ConnectionResetError:break
    if not b:break
    partial.extend(b)
  assert len(partial)<276+2880000,'Failed packing produced a complete response'
  if index==100:assert not partial,'First chunk must fail before the first pump'
  else:
   assert len(partial)>276,'Late failure did not exercise a transmitted prefix'
   h=struct.unpack('<69I',partial[:276]);assert h[3]==527 and h[4]==event and h[46]==boot
   assert h[68]==zlib.crc32(partial[:272])
  time.sleep(.15)
  with socket.create_connection(('169.254.200.10',9133),timeout=3) as s:
   s.sendall(struct.pack('<4I',MAGIC,1,255,14));header=exact(s,276);h=struct.unpack('<69I',header);body=exact(s,h[2])
  assert h[3]==15 and h[2]==FRAME_BYTES and h[4]==event and h[46]==boot
  assert h[68]==zlib.crc32(header[:272]) and zlib.crc32(body)!=h[47]
  expected=bytearray(raw);struct.pack_into('<I',expected,index*4,bad);assert body==expected
  c=EventTCP('169.254.200.10',packed=True);before_reject=c.stats()
  try:c.capture(255,passes=4)
  except ValueError as e:assert 'frame CRC mismatch' in str(e);rejected=True
  else:raise AssertionError('Corrupted canonical bytes accepted')
  c.close();time.sleep(.15);patch(boot,event,slot,index,bad,old,f'restore_{index}');changed=False
  c=EventTCP('169.254.200.10',packed=True);assert c.stats()['head']==before_reject['head']
  restored,dd,mm,_=c.capture(255,passes=4)
  assert restored==raw and dd==d and c.last_timing['wire_codec']=='RAW32'
  c.ack(mm[2],dd[0]);next_raw,nd,nm,_=c.capture(255,passes=4)
  assert nd[0]!=event and c.last_timing['wire_codec']=='BGR24_MASK1' and c.last_timing['pixel_crc_verified']
  c.ack(nm[2],nd[0])
  result=dict(passed=True,pixel=index,boot=boot,event=event,frame=d[2],slot=slot,partial_bytes=len(partial),original=old,changed=bad,
              raw_fallback_preserved_all_bits=True,host_crc_rejected=rejected,no_ack_on_failure=True,restored_sha256=hashlib.sha256(restored).hexdigest(),next_event=nd[0],next_event_packed=True)
  (O/f'case_{index}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return result
 finally:
  c.close()
  if changed:patch(boot,event,slot,index,bad,old,f'emergency_restore_{index}')

def run():
 wait_idle();action('display',value='station_6');time.sleep(.5);c=EventTCP('169.254.200.10',packed=True)
 try:
  assert c.stats()['version']==0x11a00
  while c.stats()['depth']:
   _,d,m,_=c.capture(255,passes=4);c.ack(m[2],d[0])
  c.configure(255,passes=4);time.sleep(.3);before=c.stats()
 finally:c.close()
 action('display',value='transport_noise');time.sleep(.5)
 try:
  cases=[case(100),case(800000)]
  c=EventTCP('169.254.200.10');after=c.stats();c.close()
  for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert before[k]==after[k],k
  result=dict(passed=True,real_ddr_mutation=True,cases=cases,before=before,after=after)
  (O/'summary.json').write_text(json.dumps(result,indent=2));print('Actual early/late DDR corruption, aborted partial reply, RAW rejection and new-event recovery passed',flush=True)
 finally:action('display',value='station_6')
if __name__=='__main__':run()
