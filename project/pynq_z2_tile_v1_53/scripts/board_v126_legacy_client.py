"""Run the unmodified, finalized V1.24 client against V1.26 firmware."""
from pathlib import Path
import sys,json,time,hashlib,urllib.request
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_24';sys.path.insert(0,str(B/'host'))
import tcp_transport
EventTCP=tcp_transport.EventTCP
def action(op,**kw):
 r=urllib.request.Request('http://127.0.0.1:8770/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(r,timeout=15))
def run():
 module=Path(tcp_transport.__file__);assert module==B/'host/tcp_transport.py'
 sha=hashlib.sha256(module.read_bytes()).hexdigest();manifest=json.loads((B/'DELIVERY_MANIFEST.json').read_text())
 assert sha==manifest['source_sha256']['host/tcp_transport.py']
 action('pause');time.sleep(.3);action('disconnect');c=EventTCP('169.254.200.10');rows=[]
 try:
  for source,t in [('real_000',90),('transport_noise',255)]:
   action('display',value='station_6');time.sleep(.4)
   while c.stats()['depth']:
    _,d,m,_=c.capture(t,passes=4);c.ack(m[2],d[0])
   c.configure(t,passes=4);time.sleep(.3);action('display',value=source);time.sleep(.5)
   c.compression=True;a,d,m,_=c.capture(t,passes=4);ta=dict(c.last_timing)
   c.compression=False;b,dd,mm,_=c.capture(t,passes=4);assert a==b and d==dd
   assert m[1]==0x11a00 and ta['wire_codec']==('WORD_RLE' if source=='real_000' else 'RAW32')
   assert all(ta[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   c.ack(m[2],d[0]);rows.append(dict(source=source,event=d[0],exact=True,timing=ta))
  (R/'reports/v132/legacy_client.json').write_text(json.dumps(dict(passed=True,unmodified_v124_module_sha256=sha,cases=rows),indent=2));print('Unmodified V1.24 client passed actual RLE and RAW32 compatibility',flush=True)
 finally:c.close();action('display',value='station_6')
if __name__=='__main__':run()
