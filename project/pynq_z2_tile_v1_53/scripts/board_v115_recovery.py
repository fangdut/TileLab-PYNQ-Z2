"""Fault-inject only the local TCP test path; actual pixels still come from PL.
Never changes Windows adapters or blocks unrelated network traffic.
"""
from pathlib import Path
import sys,json,time,socket,struct,threading,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from workstation import Station,EthernetBridge
from tcp_transport import EventTCP
from word_rle import decode
from board_v18_continuous import action,wait_idle
OUT=R/'reports/v132/recovery';OUT.mkdir(parents=True,exist_ok=True)

def exact(sock,n):
    result=bytearray()
    while len(result)<n:
        b=sock.recv(min(n-len(result),65536))
        if not b:raise ConnectionError('End of test connection')
        result.extend(b)
    return bytes(result)

def reset(sock):
    if sock is None:return
    try:sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('HH',1,0))
    except OSError:pass
    sock.close()

class FaultProxy:
    def __init__(self,outage=0,drop_ack=False,corrupt=False,cut_payload=False,corrupt_crc=False,corrupt_rle=False,corrupt_identity=None):
        self.until=time.monotonic()+outage;self.drop_ack=drop_ack;self.corrupt=corrupt;self.cut_payload=cut_payload
        self.corrupt_identity=corrupt_identity;self.identity_proof=None;self.corrupt_rle=corrupt_rle;self.corruption_proof=None;self.corrupt_crc=corrupt_crc;self.injected=False;self.requests=[];self.frames=[];self.rejected=0;self.ack_proof=None;self.stop=False
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen();self.listener.settimeout(.1)
        self.port=self.listener.getsockname()[1];self.clients=[]
        self.worker=threading.Thread(target=self.loop,daemon=True);self.worker.start()
    def loop(self):
        while not self.stop:
            try:conn,_=self.listener.accept()
            except socket.timeout:continue
            except OSError:break
            if time.monotonic()<self.until:self.rejected+=1;reset(conn);continue
            board=None;self.clients=[conn]
            try:
                conn.settimeout(5);board=socket.create_connection(('169.254.200.10',9133),timeout=3);self.clients.append(board)
                while not self.stop:
                    req=exact(conn,16);q=struct.unpack('<4I',req);self.requests.append(q);board.sendall(req)
                    prefix=exact(board,272);h=struct.unpack('<68I',prefix);head=prefix+(exact(board,4) if h[3]&4 else b'');body=exact(board,h[2]) if h[2] else b''
                    if q[1]==1:
                        raw=decode(body,3686400) if h[3]>>8 else body
                        self.frames.append(dict(event=h[4],frame=h[6],boot=h[46],version=h[45],sha256=hashlib.sha256(raw).hexdigest(),desc=list(h[4:44])))
                    if self.drop_ack and q[1]==2 and not self.injected:
                        self.injected=True;self.until=time.monotonic()+1.2
                        self.ack_proof=dict(requested_event=q[3],board_head=h[48],response_deliberately_dropped=True)
                        break
                    if self.cut_payload and q[1]==1 and not self.injected:
                        self.injected=True;self.until=time.monotonic()+1.2;conn.sendall(head+body[:1000]);break
                    if self.corrupt and q[1]==1 and not self.injected:
                        assert h[3]>>8==0,'Corruption test requires raw mode'
                        self.injected=True;body=bytearray(body);body[11000]^=1
                        self.corruption_proof=dict(mask_unchanged=body[3::4]==raw[3::4],rgb_changed=body!=raw)
                    if self.corrupt_rle and q[1]==1 and not self.injected:
                        assert h[3]>>8==1,'Compressed fault test did not receive RLE'
                        self.injected=True;body=bytearray(body);body[4]^=1
                        damaged=decode(body,3686400)
                        self.corruption_proof=dict(mask_unchanged=damaged[3::4]==raw[3::4],rgb_changed=damaged!=raw)
                    if self.corrupt_crc and q[1]==1 and not self.injected:
                        self.injected=True;hh=list(h);hh[47]^=1;head=struct.pack('<68I',*hh)+head[272:]
                    if self.corrupt_identity and q[1]==1 and not self.injected:
                        self.injected=True;index={'frame':6,'product':41}[self.corrupt_identity];hh=list(h);hh[index]^=1
                        self.identity_proof=dict(field=self.corrupt_identity,original=h[index],damaged=hh[index])
                        head=struct.pack('<68I',*hh)+head[272:]
                    conn.sendall(head+body)
            except (OSError,ConnectionError):pass
            finally:reset(board);reset(conn);self.clients=[]
    def close(self):
        self.stop=True;reset(self.listener)
        for s in list(self.clients):reset(s)
        self.worker.join(5)

def await_condition(fn,seconds):
    end=time.monotonic()+seconds
    while not fn():
        if time.monotonic()>end:raise TimeoutError('Recovery test condition timed out')
        time.sleep(.03)

def case(name,**kwargs):
    root=OUT/name;root.mkdir(exist_ok=False)
    proxy=FaultProxy(**kwargs);bridge=EthernetBridge('127.0.0.1');bridge.transport.port=proxy.port
    if (kwargs.get('corrupt') or kwargs.get('corrupt_crc')):bridge.transport.compression=False
    s=Station(root,bridge);begin=time.monotonic();states=[]
    try:
        s.action(dict(op='capture'))
        def finished():
            v=s.state();states.append(dict(elapsed=time.monotonic()-begin,captures=v['captures'],busy=v['busy'],error=v['error'],recovery=v['recovery'],pending_operation=v['pending_operation']))
            if (kwargs.get('corrupt') or kwargs.get('corrupt_crc') or kwargs.get('corrupt_rle') or kwargs.get('corrupt_identity')):return bool(v['error']) and not v['busy']
            if kwargs.get('outage',0)>30:return v['recovery']['exhausted'] and not v['busy']
            return v['recovery']['recovered']>=1 and not v['busy']
        await_condition(finished,40)
        st=s.state();rows=s.records.all();ops=[q[1] for q in proxy.requests]
        if (kwargs.get('corrupt') or kwargs.get('corrupt_crc') or kwargs.get('corrupt_rle') or kwargs.get('corrupt_identity')):
            assert 'CRC mismatch' in st['error'];assert not rows and st['recovery']['episodes']==0 and 2 not in ops and not st['enabled']
            if proxy.corruption_proof:assert all(proxy.corruption_proof.values())
        elif kwargs.get('outage',0)>30:
            assert not rows and not st['enabled'] and st['recovery']['exhausted'] and not ops
        else:
            assert len(rows)==1 and s.pending_ack is None and not s.pending_stats and not st['error']
            assert rows[0]['pixel_crc_verified'] and rows[0]['header_crc_verified'] and rows[0]['descriptor_crc_verified'];assert st['captures']==1 and all(f['version']==0x10f00 for f in proxy.frames)
            if kwargs.get('cut_payload'):
                assert len(proxy.frames)>=2 and len({f['sha256'] for f in proxy.frames})==1
                assert all(f['desc']==proxy.frames[0]['desc'] for f in proxy.frames)
            if kwargs.get('drop_ack'):
                assert ops.count(1)==1 and ops.count(2)==1 and ops.count(3)>=2
                assert s.records.confirmations.history()[0]['status']=='ALREADY_ACKNOWLEDGED'
                assert proxy.ack_proof['requested_event']==proxy.ack_proof['board_head']
        result=dict(passed=True,case=name,seconds=time.monotonic()-begin,request_ops=ops,rejected_connections=proxy.rejected,frames=proxy.frames,ack_proof=proxy.ack_proof,corruption_proof=proxy.corruption_proof,identity_proof=proxy.identity_proof,state=st,states=states)
        (OUT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(case=name,passed=True,seconds=result['seconds'],ops=ops,recovered=st['recovery']['recovered']),ensure_ascii=False),flush=True)
        return result
    except Exception as e:
        (OUT/(name+'_failure.json')).write_text(json.dumps(dict(error=str(e),requests=proxy.requests,frames=proxy.frames,states=states),indent=2));raise
    finally:s.exit=True;s.worker.join(6);bridge.close();proxy.close();s.records.db.close();time.sleep(.2)

def run():
    wait_idle();action('display',value='station_6');time.sleep(.5)
    c=EventTCP('169.254.200.10');before=c.stats();assert before['version']==0x10f00
    while c.stats()['depth']:
        _,d,m,_=c.capture(89);c.ack(m[2],d[0])
    c.close();action('display',value='real_000');time.sleep(.5)
    try:
        results=[case('initial_3s_outage',outage=3),case('payload_cut',cut_payload=True),case('ack_reply_lost',drop_ack=True),case('corrupt_rgb',corrupt=True)]
        # Damaged wire data was deliberately left unconfirmed. Re-read the
        # original hardware event directly, verify it, then explicitly ACK it.
        bridge=EthernetBridge('169.254.200.10');f,im,mask=bridge.capture(89)
        assert f['event_id']==results[-1]['frames'][0]['event'];bridge.ack(f);bridge.close();time.sleep(.2)
        results.append(case('corrupt_rle_rgb',corrupt_rle=True))
        bridge=EthernetBridge('169.254.200.10');f,im,mask=bridge.capture(89)
        assert f['event_id']==results[-1]['frames'][0]['event'] and f['pixel_crc_verified'];bridge.ack(f);bridge.close();time.sleep(.2)
        results.append(case('corrupt_crc',corrupt_crc=True))
        bridge=EthernetBridge('169.254.200.10');f,im,mask=bridge.capture(89)
        assert f['event_id']==results[-1]['frames'][0]['event'] and f['pixel_crc_verified'];bridge.ack(f);bridge.close();time.sleep(.2)
        for field in ('frame','product'):
            results.append(case('corrupt_'+field,corrupt_identity=field))
            bridge=EthernetBridge('169.254.200.10');f,im,mask=bridge.capture(89)
            original=results[-1]['frames'][0]
            assert f['event_id']==original['event'] and f['frame_id']==original['frame'] and f['product_id']==original['desc'][37]
            assert f['pixel_crc_verified'] and f['header_crc_verified'] and f['descriptor_crc_verified'];bridge.ack(f);bridge.close();time.sleep(.2)
        results.append(case('bounded_30s_outage',outage=60))
        c=EventTCP('169.254.200.10');after=c.stats();c.close()
        assert after['descriptor_crc_errors']==before['descriptor_crc_errors'] and after['descriptor_verified_frames']==after['captured']
        assert after['gaps']==before['gaps'] and after['dropped']==before['dropped'] and after['invalid']==before['invalid'] and after['ack_errors']==before['ack_errors']
        summary=dict(passed=True,tests=9,before=before,after=after,cases=[dict(name=r['case'],seconds=r['seconds'],recovered=r['state']['recovery']['recovered'],saved=r['state']['records_total']) for r in results],scope='Actual HDMI/FPGA frames through local fault proxy; no physical unplug/power-cycle claim')
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    finally:action('display',value='station_6')
if __name__=='__main__':run()
