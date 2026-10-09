"""Additional real PACK25 corruption, reconnect and ACK-loss cases."""
from pathlib import Path
import sys,time,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
import board_v126_recovery as test
from tcp_transport import EventTCP
from board_v18_continuous import action,wait_idle

def run():
 wait_idle();action('display',value='station_6');time.sleep(.5)
 c=EventTCP('169.254.200.10',packed=True);before=c.stats();assert before['version']==0x11a00
 while c.stats()['depth']:
  _,d,m,_=c.capture(255,passes=4);c.ack(m[2],d[0])
 c.configure(255,passes=4);time.sleep(.4);c.close();action('display',value='transport_noise');time.sleep(.5)
 try:
  results=[]
  for name,args in [('packed_color_corrupt',dict(corrupt_packed='color')),('packed_mask_corrupt',dict(corrupt_packed='mask')),('packed_payload_cut',dict(cut_payload=True)),('packed_ack_lost',dict(drop_ack=True))]:
   r=test.case(name,**args);assert r['frames'] and all(f['codec']==2 for f in r['frames']);results.append(r)
   if args.get('corrupt_packed'):
    c=EventTCP('169.254.200.10',packed=True);c.stats();raw,d,m,_=c.capture(255,passes=4)
    assert d[0]==r['frames'][0]['event'] and c.last_timing['pixel_crc_verified']
    assert c.last_timing['wire_codec']=='BGR24_MASK1';c.ack(m[2],d[0]);c.close();time.sleep(.2)
  c=EventTCP('169.254.200.10',packed=True);after=c.stats();c.close()
  for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert before[k]==after[k],k
  summary=dict(passed=True,tests=4,before=before,after=after,cases=[dict(name=r['case'],seconds=r['seconds'],saved=r['state']['records_total'],codecs=[f['codec'] for f in r['frames']]) for r in results])
  (R/'reports/v132/packed_faults.json').write_text(json.dumps(summary,indent=2));print('Four additional PACK25 fault cases passed',flush=True)
 finally:action('display',value='station_6');c.close()
if __name__=='__main__':run()
