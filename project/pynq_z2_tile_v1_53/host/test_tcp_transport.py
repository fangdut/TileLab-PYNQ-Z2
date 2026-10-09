import socket,threading,struct,unittest,time
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES

class TCPTests(unittest.TestCase):
 def test_capture_transmits_explicit_algorithm_mode(self):
  for enhance,want in ((True,0),(False,1)):
   listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1];requests=[]
   def serve():
    conn,_=listener.accept()
    with conn:
     req=b''
     while len(req)<16:req+=conn.recv(16-len(req))
     requests.append(struct.unpack('<4I',req))
     conn.sendall(struct.pack('<68I',MAGIC,0,FRAME_BYTES,0,*([0]*64))+bytes(FRAME_BYTES))
    listener.close()
   th=threading.Thread(target=serve);th.start();c=EventTCP('127.0.0.1',port)
   try:c.capture(89,enhance=enhance)
   finally:c.close();th.join(3)
   self.assertEqual(requests,[(MAGIC,1,89,want|2)])
 def server(self,response):
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1]
  def serve():
   conn,_=listener.accept()
   try:
    received=b''
    while len(received)<16:received+=conn.recv(16-len(received))
    for chunk in response:conn.sendall(chunk)
   except (ConnectionError,OSError):pass
   finally:conn.close();listener.close()
  th=threading.Thread(target=serve);th.start();return EventTCP('127.0.0.1',port),th
 def test_split_header_and_frame(self):
  header=struct.pack('<68I',MAGIC,0,FRAME_BYTES,0,*([0]*64));body=b'\x5a'*FRAME_BYTES
  c,t=self.server([header[:3],header[3:107],header[107:],body[:777],body[777:]])
  raw,d,m,_=c.capture(36);self.assertEqual(raw,body);self.assertEqual(len(d),40);self.assertEqual(len(m),24);c.close();t.join()
 def test_truncated_payload_and_oversized_header_rejected(self):
  for size,payload in [(FRAME_BYTES,b'incomplete'),(0xffffffff,b'')]:
   h=struct.pack('<68I',MAGIC,0,size,0,*([0]*64));c,t=self.server([h,payload])
   # A retry to the now-closed listener can fail by refusal or connect timeout.
   with self.assertRaises((ValueError,OSError)):c.capture(36)
   self.assertIsNone(c.sock);t.join()
 def test_ack_and_private_address_validation(self):
  m=[0]*24;m[0]=0x54494c33;m[2]=7;m[4]=9
  h=struct.pack('<68I',MAGIC,1,0,0,*([0]*40),*m);c,t=self.server([h]);c.ack(7,9);c.close();t.join()
  for address in ('8.8.8.8','224.0.0.1','0.0.0.0'):
   with self.assertRaises(ValueError):EventTCP(address)
 def test_status_metadata(self):
  m=[0]*24;m[0]=0x54494c33;m[2]=123;m[6]=7;m[8]=4
  h=struct.pack('<68I',MAGIC,1,0,1,*([0]*40),*m)
  c,t=self.server([h]);s=c.stats();c.close();t.join()
  self.assertEqual(s['boot_id'],123);self.assertEqual(s['depth'],7);self.assertEqual(s['dropped'],4)
 def test_probe_counter_is_versioned_and_uses_status_extension(self):
  for version in (0x10700,0x10800):
   m=[0]*24;m[0]=0x54494c33;m[1]=version;d=[0]*40;d[39]=123
   c,t=self.server([struct.pack('<68I',MAGIC,1,0,1,*d,*m)])
   try:s=c.stats()
   finally:c.close();t.join()
   if version==0x10800:self.assertEqual(s['compression_probe_bypasses'],123)
   else:self.assertNotIn('compression_probe_bypasses',s)
 def test_reconnect_after_partial_frame(self):
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1];requests=[]
  body=b'\x37'*FRAME_BYTES;h=struct.pack('<68I',MAGIC,0,FRAME_BYTES,1,*([0]*64))
  def serve():
   try:
    for i in range(2):
     conn,_=listener.accept();conn.settimeout(3)
     with conn:
      req=b''
      while len(req)<16:req+=conn.recv(16-len(req))
      requests.append(req);conn.sendall(h);conn.sendall(body[:91] if i==0 else body)
   finally:listener.close()
  th=threading.Thread(target=serve,daemon=True);th.start();c=EventTCP('127.0.0.1',port)
  try:raw,*_=c.capture(36);self.assertEqual(raw,body);self.assertEqual(requests[0],requests[1]);self.assertGreater(c.last_timing['payload_MB_s'],0)
  finally:c.close();th.join(3)

 def test_stalled_tail_restarts_without_ack_or_long_pause(self):
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1];requests=[]
  body=b'\x28'*FRAME_BYTES;h=struct.pack('<68I',MAGIC,0,FRAME_BYTES,1,*([0]*64))
  def serve():
   try:
    for i in range(2):
     conn,_=listener.accept();conn.settimeout(4)
     with conn:
      req=b''
      while len(req)<16:req+=conn.recv(16-len(req))
      requests.append(req);conn.sendall(h);conn.sendall(body[:-846] if i==0 else body)
      if i==0:self.assertEqual(conn.recv(16),b'')
   finally:listener.close()
  th=threading.Thread(target=serve,daemon=True);th.start();c=EventTCP('127.0.0.1',port);begun=time.perf_counter()
  try:
   raw,*_=c.capture(36);self.assertEqual(raw,body);self.assertEqual(requests[0],requests[1]);self.assertEqual(c.last_timing['retry_count'],1)
   self.assertLess(time.perf_counter()-begun,3);self.assertEqual(c.failures[0]['bytes_received'],272+FRAME_BYTES-846)
  finally:c.close();th.join(3)

if __name__=='__main__':unittest.main(verbosity=2)
