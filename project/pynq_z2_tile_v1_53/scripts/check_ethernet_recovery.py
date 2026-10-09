"""Physical-board TCP interruption and idempotent ACK acceptance."""
from pathlib import Path
import hashlib,json,socket,struct,sys,time
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP,MAGIC
from workstation import Bridge,Records

address='169.254.200.10';out=R/'reports/ethernet_20260926/recovery.json'
c=EventTCP(address);records=Records(R);result=dict(kind='REAL_BOARD',checks=[],passed=False)
try:
    raw,d,m,_=c.capture(36);identity=(d[34],d[0]);digest=hashlib.sha256(raw).hexdigest()
    f,image,mask=Bridge.decode_event(raw,d,m,0)
    # Persist before any deliberate ACK test. No synthetic test server here.
    records.save(f,image,mask,'ethernet_recovery_acceptance')
    c.close();time.sleep(.3)
    broken=socket.create_connection((address,9133),timeout=5)
    broken.sendall(struct.pack('<4I',MAGIC,1,36,0))
    prefix=broken.recv(4096);assert prefix
    broken.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0));broken.close();time.sleep(.3)
    raw2,d2,m2,_=c.capture(36)
    assert (d2[34],d2[0])==identity and hashlib.sha256(raw2).hexdigest()==digest
    result['checks'].append(dict(test='mid_frame_disconnect_retains_identical_event',passed=True,boot=identity[0],event=identity[1],sha256=digest))
    c.ack(*identity);after=c.stats();c.ack(*identity);again=c.stats()
    assert after['head']==again['head']==identity[1] and again['ack_errors']==after['ack_errors']==0
    result['checks'].append(dict(test='repeat_ack_does_not_release_next_event',passed=True,after=again))
    c.close();time.sleep(.3)
    bad=socket.create_connection((address,9133),timeout=5);bad.sendall(struct.pack('<4I',0,1,36,0))
    try:closed=bad.recv(1)==b''
    except ConnectionResetError:closed=True
    bad.close();assert closed;time.sleep(.3)
    assert c.stats()['head']==identity[1]
    result['checks'].append(dict(test='malformed_request_rejected_without_queue_release',passed=True))
    # Server's 30s peer timeout must not leave a paused receiver permanently stuck.
    before=c.stats();time.sleep(32);after=c.stats()
    assert before['boot_id']==after['boot_id'] and before['head']==after['head']
    result['checks'].append(dict(test='idle_timeout_reconnect_preserves_queue',passed=True))
    result['passed']=True
except Exception as e:
    result['error']=repr(e);raise
finally:
    out.write_text(json.dumps(result,indent=2));c.close();records.db.close();print(json.dumps(result,indent=2))
