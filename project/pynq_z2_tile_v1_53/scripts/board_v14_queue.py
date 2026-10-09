"""Product-level capacity and broken-TCP recovery on the physical board."""
from board_v14_continuous import *
from tcp_transport import EventTCP,MAGIC
OUT=R/'reports/v14/queue';OUT.mkdir(parents=True,exist_ok=True)
wait_idle();action('display',value='station_6');time.sleep(.5)
b=EthernetBridge('169.254.200.10');rec=Records(R);held=[]
try:
 while b.stats()['depth']:
  f,im,ma=b.capture(36)
  if f['event_reason'] in (1,2):rec.save(f,im,ma,'hardware_alarm')
  b.ack(f)
 before=b.stats()
 for n in range(16):
  action('display',value='station_4');time.sleep(.45);action('display',value='station_6');time.sleep(.45)
 after=b.stats();result=dict(before=before,after=after,event_delta=after['events']-before['events'],drop_delta=after['dropped']-before['dropped'])
 assert result['event_delta']==16 and result['drop_delta']==4 and after['depth']==12,result
 # Download first held event but deliberately do not ACK it. Closing halfway
 # through the next transfer must leave both frame content and identity intact.
 f,im,ma=b.capture(36);first=dict(frame=f,image_sha256=hashlib.sha256(im).hexdigest(),mask_sha256=hashlib.sha256(ma).hexdigest());b.close();time.sleep(.15)
 s=socket.create_connection(('169.254.200.10',9133),timeout=2);s.sendall(struct.pack('<4I',MAGIC,1,36,0));partial=s.recv(4096);s.close();time.sleep(.2)
 f2,im2,ma2=b.capture(36);assert f2['event_id']==f['event_id'] and f2['product_id']==f['product_id'] and im2==im and ma2==ma
 result['partial_reconnect']=dict(bytes_received=len(partial),same_event=True,same_pixels=True)
 for n in range(12):
  if n==0:f,im,ma=f2,im2,ma2
  else:f,im,ma=b.capture(36)
  actual=np.asarray(Image.open(io.BytesIO(ma)))>0;expected,_=detect(Image.open(io.BytesIO(im)));rr=regions(expected)
  assert np.array_equal(actual,expected) and f['boxes']==rr['boxes'] and f['selection_full_tile'] and f['selection']=='FPGA_PRODUCT_BEST_FRAME'
  key=rec.save(f,im,ma,'hardware_alarm');held.append(dict(key=key,**f));b.ack(f);b.ack(f)
 final=b.stats();result.update(final=final,first=first,held=held,passed=final['depth']==0 and final['ack_errors']==0 and len({f['product_id'] for f in held})==12)
 (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('first','held')}),flush=True);assert result['passed']
except Exception as e:
 (OUT/'failure.json').write_text(json.dumps(dict(error=str(e),held=held,failures=b.transport.failures),indent=2));raise
finally:action('display',value='station_6');b.close();rec.db.close()
