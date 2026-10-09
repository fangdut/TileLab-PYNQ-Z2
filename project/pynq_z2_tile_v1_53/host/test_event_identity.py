import unittest,tempfile,json,struct,zlib,threading,csv,io,urllib.request
from types import SimpleNamespace
from event_identity import decode_event_identity
from workstation import Bridge,Records,handler,ThreadingHTTPServer
from test_events import packet
import test_descriptor_crc as wire

def frame(generation=0):
 raw,d,m=packet();m[1]=0x11500;d[8]=(generation<<8)|1
 return Bridge.decode_event(raw,d,m,1)

class EventIdentityTests(unittest.TestCase):
 def test_generation_and_reason_are_decoded_independently(self):
  for generation in range(4):
   for reason in (1,2,3):
    raw,d,m=packet();m[1]=0x11500;d[8]=(generation<<8)|reason
    f,_,_=Bridge.decode_event(raw,d,m,1)
    self.assertEqual((f['event_reason'],f['recovery_generation']),(reason,generation))
    self.assertEqual(f['firmware_version'],0x11500)
 def test_legacy_generation_is_unknown_not_zero(self):
  for version in (0,0x10400,0x11400):
   self.assertEqual(decode_event_identity(1,version),dict(event_reason=1,recovery_generation=None))
 def test_reserved_generation_reason_and_non_words_rejected(self):
  for value in (0,4,256,0x401,0x80000001,-1,2**32,True,None):
   with self.assertRaises(ValueError):decode_event_identity(value,0x11500)
 def test_changed_generation_cannot_reuse_existing_evidence(self):
  f,img,mask=frame(1)
  with tempfile.TemporaryDirectory() as p:
   s=Records(p)
   try:
    key=s.save(f,img,mask,'manual');s.update(key,'needs_recheck','Keep human review')
    self.assertEqual(key,s.save(f,img,mask,'manual'))
    with self.assertRaisesRegex(ValueError,'identity'):s.save(dict(f,recovery_generation=2),img,mask,'manual')
    self.assertEqual(s.all()[0]['note'],'Keep human review')
   finally:s.db.close()
 def test_restart_confirmation_retains_generation_and_rejects_tampering(self):
  f,img,mask=frame(2)
  with tempfile.TemporaryDirectory() as p:
   s=Records(p);key=s.save(f,img,mask,'manual',confirmation_endpoint='tcp:169.254.200.10');s.db.close();s=Records(p)
   try:
    pending=s.confirmations.pending();self.assertEqual(pending['frame']['recovery_generation'],2)
    with self.assertRaisesRegex(ValueError,'generation'):s.confirmations.settle(dict(f,recovery_generation=1),'ACKNOWLEDGED')
    bad=dict(pending);bad['frame']=dict(pending['frame'],recovery_generation=1)
    s.db.execute('UPDATE pending_confirmation SET payload=?',(json.dumps(bad),));s.db.commit()
    with self.assertRaisesRegex(ValueError,'identity'):s.confirmations.pending()
    s.db.execute('UPDATE pending_confirmation SET payload=?',(json.dumps(pending),));s.db.commit()
    s.confirmations.settle(f,'ACKNOWLEDGED');self.assertEqual(s.confirmations.history()[0]['frame']['recovery_generation'],2)
   finally:s.db.close()
 def test_legacy_journal_without_field_can_be_retried(self):
  f,img,mask=Bridge.decode_event(*packet(),1)
  f.pop('recovery_generation')
  with tempfile.TemporaryDirectory() as p:
   s=Records(p)
   try:
    key=s.save(f,img,mask,'manual',confirmation_endpoint='old')
    pending=s.confirmations.pending();pending['frame'].pop('recovery_generation')
    s.db.execute('UPDATE pending_confirmation SET payload=?',(json.dumps(pending),));s.db.commit()
    s.save(dict(f,recovery_generation=None),img,mask,'manual',confirmation_endpoint='old')
    self.assertIsNone(s.confirmations.pending()['frame'].get('recovery_generation'))
    s.confirmations.settle(f,'ACKNOWLEDGED')
   finally:s.db.close()
 def test_wire_header_crc_binds_generation(self):
  response,_=wire.DescriptorProtocolTests().packet(version=0x11500)
  words=list(struct.unpack('<68I',response[0][:272]));words[12]=(2<<8)|3
  head=struct.pack('<68I',*words);response[0]=head+struct.pack('<I',zlib.crc32(head))
  wire.DescriptorProtocolTests().run_packet(response)
  bad=bytearray(response[0]);bad[12*4+1]^=1;response[0]=bad
  wire.DescriptorProtocolTests().run_packet(response,'Header CRC mismatch')
 def test_real_http_exports_keep_frame_bound_generation(self):
  f,img,mask=frame(3)
  with tempfile.TemporaryDirectory() as p:
   store=Records(p);store.save(f,img,mask,'manual')
   server=ThreadingHTTPServer(('127.0.0.1',0),handler(SimpleNamespace(records=store)))
   worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    with urllib.request.urlopen(base+'/api/export') as stream:data=json.load(stream)
    self.assertEqual(data['records'][0]['recovery_generation'],3)
    with urllib.request.urlopen(base+'/api/export?format=csv') as stream:text=stream.read().decode('utf-8-sig')
    row=next(csv.DictReader(io.StringIO(text)));self.assertEqual(row['recovery_generation'],'3')
   finally:server.shutdown();server.server_close();worker.join(2);store.db.close()

if __name__=='__main__':unittest.main(verbosity=2)
