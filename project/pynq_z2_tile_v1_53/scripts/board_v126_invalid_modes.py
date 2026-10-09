"""Send invalid recipe flags to the actual firmware and verify no side effects."""
from pathlib import Path
import sys,time,json,socket,struct,zlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,MAGIC
from board_v18_continuous import action,wait_idle,read_player
O=R/'reports/v132'

def run():
 wait_idle();action('display',value='station_6');time.sleep(.6)
 c=EventTCP('169.254.200.10');rows=[]
 try:
  while c.stats()['depth']:
   _,d,m,_=c.capture(90,passes=4);c.ack(m[2],d[0])
  c.configure(90,passes=4);time.sleep(.25);initial=c.stats();assert initial['version']==0x11a00
  cases=[(1,90,k) for k in (5,7,8,9,12,13,15,16)]+[(5,90,k) for k in (2,3,5,6,7,8,10,14)]+[(op,t,4) for op in (1,5) for t in (0,256)]
  for op,t,flags in cases:
   before=c.stats();c.close()
   with socket.create_connection(('169.254.200.10',9133),timeout=3) as s:
    s.sendall(struct.pack('<4I',MAGIC,op,t,flags));data=bytearray()
    while len(data)<276:
     chunk=s.recv(276-len(data));assert chunk;data.extend(chunk)
   h=struct.unpack('<69I',data)
   assert h[0]==MAGIC and h[1]==2 and h[2]==0 and h[3]==5 and h[-1]==zlib.crc32(data[:272])
   after=c.stats()
   fields=('boot_id','config','threshold','request','request_ack','head','tail','depth','ack_errors','invalid','gaps','dropped','descriptor_crc_errors')
   assert all(after[k]==before[k] for k in fields),(op,t,flags,before,after)
   rows.append(dict(op=op,threshold=t,flags=flags,rejected=True,crc_verified=True,before=before,after=after))
  (O/'invalid_modes_board.json').write_text(json.dumps(dict(passed=True,cases=rows,scope=__doc__),indent=2));print(f'PASS {len(rows)} invalid hardware recipe/capability requests rejected without state/queue changes',flush=True)
 finally:c.close()
if __name__=='__main__':run()
