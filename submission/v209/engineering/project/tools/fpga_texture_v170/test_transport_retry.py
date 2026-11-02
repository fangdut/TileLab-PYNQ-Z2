from pathlib import Path
import sys,struct,zlib,json
from unittest.mock import patch
p=Path(__file__).resolve().parent;sys.path.insert(0,str(p));from board_client import Board,ID
class Fake:
    def __init__(self,corrupt=False):
        self.sent=[];r=[0x16905258,0,1,0,0,ID,0,0,123,0,0,100,0,0,0,0];r[15]=zlib.crc32(struct.pack('<15I',*r[:15]))^int(corrupt);self.wire=struct.pack('<16I',*r)
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def settimeout(self,*args):pass
    def sendall(self,data):self.sent.append(data)
    def recv(self,n):data=self.wire[:n];self.wire=self.wire[n:];return data
sock=Fake();board=Board()
with patch('socket.create_connection',side_effect=[TimeoutError('connect1'),TimeoutError('connect2'),sock]) as connect,patch('time.sleep'):
    board.request(1);assert connect.call_count==3 and board.connection_retries==2
    assert len([x for x in sock.sent if x])==1 and struct.unpack('<16I',sock.sent[0])[2]==1
    assert all(call.kwargs['timeout']==0.5 for call in connect.call_args_list)
sock=Fake(corrupt=True);board=Board()
with patch('socket.create_connection',return_value=sock) as connect:
    try:board.request(1)
    except RuntimeError:pass
    else:raise AssertionError('Corrupt reply accepted')
    assert connect.call_count==1 and board.connection_retries==0
with patch('socket.create_connection',side_effect=TimeoutError('offline')) as connect,patch('time.sleep'):
    try:Board().request(1)
    except TimeoutError:pass
    else:raise AssertionError('Offline board accepted')
    assert connect.call_count==3
sock=Fake();board=Board(timeout=15)
with patch('socket.create_connection',return_value=sock) as connect,patch.object(sock,'recv',side_effect=TimeoutError('reply timeout')):
    try:board.request(1)
    except TimeoutError:pass
    else:raise AssertionError('Sent request replayed after receive timeout')
    assert connect.call_count==1 and len([x for x in sock.sent if x])==1 and board.connection_retries==0
sock=Fake()
with patch('socket.create_connection',return_value=sock) as connect:
    Board(connect_timeout=3).request(1);assert connect.call_args.kwargs['timeout']==3
print(json.dumps(dict(scope='TRANSPORT_MOCK_TESTS_NOT_BOARD',retry_before_send=True,no_replay_after_corrupt_reply=True,no_replay_after_receive_timeout=True,local_connect_timeout=0.5,remote_override_supported=True,attempt_limit=3,passed=True)))
