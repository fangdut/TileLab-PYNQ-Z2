"""Real pinned DDR mask corruption must use RAW fallback and fail PL CRC."""
from pathlib import Path
import sys,time,json,struct,subprocess,socket,zlib,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/noncanonical';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'));from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
from board_v18_continuous import action,wait_idle

def patch(boot,event,slot,idx,old,new,name):
 with (O/(name+'.log')).open('wb') as f:
  p=subprocess.run(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/patch_pinned_pixel.tcl'),*[str(x) for x in (boot,event,slot,idx,old,new)]],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=0x08000000)
 p.check_returncode();assert 'PASS pinned event pixel' in (O/(name+'.log')).read_text()

def exact(s,n):
 out=bytearray()
 while len(out)<n:
  b=s.recv(min(65536,n-len(out)))
  if not b:raise ConnectionError('Truncated test reply')
  out.extend(b)
 return out

def run():
 wait_idle();action('display',value='station_6');time.sleep(.5);c=EventTCP('169.254.200.10',packed=True);changed=False
 try:
  while c.stats()['depth']:
   _,d,m,_=c.capture(255,passes=4);c.ack(m[2],d[0])
  c.configure(255,passes=4);time.sleep(.3);action('display',value='transport_noise');time.sleep(.5)
  before=c.stats();raw,d,m,_=c.capture(255,passes=4);assert c.last_timing['wire_codec']=='BGR24_MASK1'
  slot=d[1];index=100;old=struct.unpack_from('<I',raw,index*4)[0];bad=old^(1<<25);boot=m[2];event=d[0];c.close();time.sleep(.1)
  changed=True;patch(boot,event,slot,index,old,bad,'inject')
  with socket.create_connection(('169.254.200.10',9133),timeout=3) as s:
   s.sendall(struct.pack('<4I',MAGIC,1,255,14));header=exact(s,276);h=struct.unpack('<69I',header);body=exact(s,h[2])
  assert h[3]==15 and h[2]==FRAME_BYTES and h[4]==event and h[46]==boot
  assert h[68]==zlib.crc32(header[:272]) and zlib.crc32(body)!=h[47]
  expected=bytearray(raw);struct.pack_into('<I',expected,index*4,bad);assert body==expected
  c=EventTCP('169.254.200.10',packed=True);c.stats()
  try:c.capture(255,passes=4)
  except ValueError as e:assert 'frame CRC mismatch' in str(e);rejected=True
  else:raise AssertionError('Corrupted canonical bytes accepted')
  c.close();time.sleep(.1);patch(boot,event,slot,index,bad,old,'restore');changed=False
  c=EventTCP('169.254.200.10',packed=True);c.stats();restored,dd,mm,_=c.capture(255,passes=4)
  assert restored==raw and dd==d and c.last_timing['wire_codec']=='BGR24_MASK1'
  c.ack(mm[2],dd[0]);after=c.stats()
  for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert before[k]==after[k],k
  result=dict(passed=True,real_ddr_mutation=True,boot=boot,event=event,frame=d[2],slot=slot,pixel=index,original=old,changed=bad,raw_fallback_preserved_all_bits=True,host_crc_rejected=rejected,restored_sha256=hashlib.sha256(restored).hexdigest(),before=before,after=after)
  (O/'summary.json').write_text(json.dumps(result,indent=2));print('Actual noncanonical DDR bit preserved by RAW fallback, rejected by CRC, restored and confirmed',flush=True)
 finally:
  c.close()
  if changed:patch(boot,event,slot,index,bad,old,'emergency_restore')
  action('display',value='station_6')
if __name__=='__main__':run()
