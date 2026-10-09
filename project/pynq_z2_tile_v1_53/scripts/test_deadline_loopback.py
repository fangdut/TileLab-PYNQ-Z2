"""Short real TCP deadline smoke on an ephemeral 127.0.0.1 port only."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import select
import socket
import struct
import sys
import threading
import time
import traceback
import zlib

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from tcp_transport import EventTCP,MAGIC,RequestDeadlineExceeded


def status_packet():
    descriptor=[0]*40;descriptor[:6]=[0x484c5431,1,0,0,0,1]
    descriptor[23:37]=[0x52454331,0,0,0,0,0,0,0,0,0,3,1000,3000,0]
    meta=[0]*24;meta[:3]=[0x54494c33,0x12500,17];meta[18]=60
    header=struct.pack('<68I',MAGIC,1,0,5,*descriptor,*meta)
    return header+struct.pack('<I',zlib.crc32(header))


def main():
    output=ROOT/'reports/v140/deadline_loopback';output.mkdir(parents=True,exist_ok=True)
    result=dict(passed=False,started_utc=datetime.now(timezone.utc).isoformat(),
        control_timeout_seconds=.3,idle_timeout_seconds=.35,server_chunk_bytes=8,server_chunk_interval_seconds=.05,
        scope='Real TCP on an ephemeral IPv4 loopback port; no board or workstation API access.',
        limitations=['The 0.3-second control budget is deliberately shortened to test the mechanism.',
                     'Default 3-second/8-second budgets require separate deterministic and board acceptance; this smoke does not establish board performance.'],
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                       for name in ('host/tcp_transport.py','scripts/test_deadline_loopback.py')})
    requests=[];send_times=[];server_errors=[];closed_observed=threading.Event();stop=threading.Event()
    listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);listener.bind(('127.0.0.1',0));listener.listen(2);listener.settimeout(3)
    port=listener.getsockname()[1];result['port']=port;assert port!=8770
    reply=status_packet()
    def serve():
        try:
            for index in range(2):
                connection,address=listener.accept();assert address[0]=='127.0.0.1';connection.settimeout(2)
                with connection:
                    request=bytearray()
                    while len(request)<16:
                        part=connection.recv(16-len(request))
                        if not part:raise AssertionError('Request closed before complete header')
                        request.extend(part)
                    values=struct.unpack('<4I',request);requests.append(list(values));assert values==(MAGIC,3,0,0)
                    if index==0:
                        for offset in range(0,len(reply),8):
                            if stop.is_set():return
                            if select.select([connection],[],[],0)[0]:
                                extra=connection.recv(16)
                                assert not extra,'Unexpected additional request/ACK after partial status'
                                closed_observed.set();break
                            try:connection.sendall(reply[offset:offset+8]);send_times.append(time.monotonic())
                            except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):
                                closed_observed.set();break
                            if stop.wait(.05):return
                        else:raise AssertionError('Slow response completed despite the short total budget')
                    else:
                        # A fresh request must receive a fresh budget, including
                        # a measurable delay after the previous deadline expired.
                        if stop.wait(.1):return
                        connection.sendall(reply)
        except Exception:server_errors.append(traceback.format_exc())
        finally:listener.close()
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    client=EventTCP('127.0.0.1',port,read_idle_timeout=.35,control_timeout=.3)
    try:
        begun=time.monotonic()
        try:client.stats()
        except RequestDeadlineExceeded as error:failure=str(error)
        else:raise AssertionError('Slow status did not hit its absolute deadline')
        elapsed=time.monotonic()-begun
        assert .25<=elapsed<.8,elapsed
        assert client.sock is None and client._request_deadline is None
        assert client.total_received_bytes>=16 and client.total_received_bytes<272
        assert client.reconnects==0,'Expired total budget must not reconnect automatically'
        first_received=client.total_received_bytes;first_failures=list(client.failures)
        assert closed_observed.wait(1),'Server did not observe timed-out connection close'
        begun=time.monotonic();stats=client.stats();second_elapsed=time.monotonic()-begun
        assert stats['boot_id']==17 and client.last_timing['header_crc_verified']
        assert .08<=second_elapsed<.5 and client._request_deadline is None
        client.close();thread.join(3);assert not thread.is_alive() and not server_errors,server_errors
        assert len(requests)==2 and all(request[1]==3 for request in requests)
        intervals=[b-a for a,b in zip(send_times,send_times[1:])]
        assert len(send_times)>=3 and all(gap<.35 for gap in intervals),intervals
        result.update(passed=True,first_request_elapsed_seconds=elapsed,exception_type='RequestDeadlineExceeded',
            first_request_error=failure,first_received_bytes=first_received,first_failures=first_failures,
            automatic_reconnects=client.reconnects,server_observed_close=True,server_send_intervals_seconds=intervals,
            second_request_elapsed_seconds=second_elapsed,second_header_crc_verified=True,
            second_boot_id=stats['boot_id'],requests=requests,no_ack_request=True,
            completed_utc=datetime.now(timezone.utc).isoformat())
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        stop.set();client.close();listener.close();thread.join(3)
        result['server_errors']=server_errors
        (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
