"""Bounded TCP framing for the optional board firmware (private lab LAN)."""
import socket,struct,ipaddress,time,zlib,math
from capture_health import decode_health
from dma_recovery import decode_recovery
from word_rle import decode as decode_rle
from packed_pixels import decode as decode_packed
MAGIC=0x544c5033;FRAME_BYTES=3686400;LOW_GATE_VERSION=0x12500;WIDE_WEAK_VERSION=0x12b00;RIDGE_VERSION=0x12c00;SUPPORT_VERSION=0x12d00;BOOST_VERSION=0x13100;BOOST_MODEL_ID=0xd06b3b9b
META_NAMES=('magic','version','boot_id','heartbeat','head','tail','depth','events','dropped','captured','invalid','ack','request','reason','request_ack','threshold','enabled','gaps','frames','last_seq','active','config','error_status','ack_errors')
class RequestDeadlineExceeded(TimeoutError):
 """One logical exchange exhausted its budget; no fresh retry window."""

class EventTCP:
 def __init__(self,address,port=9133,read_idle_timeout=.35,compression=True,packed=False,*,control_timeout=3.0,image_timeout=8.0):
  ip=ipaddress.ip_address(address)
  if ip.version!=4 or not ip.is_private or ip.is_unspecified or ip.is_multicast:raise ValueError('Use a private IPv4 address on the lab LAN')
  if not .1<=read_idle_timeout<=10:raise ValueError('Invalid receive idle timeout')
  if type(compression) is not bool:raise ValueError('Compression must be Boolean')
  if type(packed) is not bool:raise ValueError('Packed capability must be Boolean')
  if any(type(value) not in (int,float) or not math.isfinite(value) or value<=0 for value in (control_timeout,image_timeout)):
   raise ValueError('Logical request timeouts must be finite positive seconds')
  self.control_timeout=float(control_timeout);self.image_timeout=float(image_timeout)
  self._request_deadline=None;self._receive_timeout=read_idle_timeout
  self.packed=packed;self.peer_version=0
  self.compression=compression
  self.address=str(ip);self.port=port;self.read_idle_timeout=read_idle_timeout;self.first_frame=True;self.sock=None;self.last_timing={};self.reconnects=0;self.failures=[];self.stage='idle';self.bytes_received=0
  self.total_received_bytes=0;self.requests_sent=0
 def close(self):
  if self.sock:self.sock.close();self.sock=None
 def _remaining(self):
  if self._request_deadline is None:return None
  remaining=self._request_deadline-time.monotonic()
  if remaining<=0:raise RequestDeadlineExceeded('Logical TCP request deadline exceeded during '+self.stage)
  return remaining
 def _socket_timeout(self,idle):
  remaining=self._remaining()
  self.sock.settimeout(idle if remaining is None else min(idle,remaining))
 def exact(self,n):
  result=bytearray(n);view=memoryview(result);offset=0
  while offset<n:
   # Positive progress resets the socket idle wait, never the total budget.
   self._socket_timeout(self._receive_timeout)
   count=self.sock.recv_into(view[offset:],min(65536,n-offset))
   if not count:raise ConnectionError('Incomplete TCP event; board ACK not sent')
   offset+=count
   self.bytes_received+=count
   self.total_received_bytes+=count
   self._remaining()
  return result
 def exchange(self,op,a,b=0):
  # A capture never frees an event. ACK is idempotent for this boot/event.
  # Retry only broken connections, never a malformed/mismatched response.
  begun=time.perf_counter()
  self._request_deadline=time.monotonic()+(self.image_timeout if op==1 else self.control_timeout)
  try:
   for attempt in range(2):
    try:
     if attempt:
      self.stage='retry_wait'
      # Backoff belongs to the same request, including when only part of the
      # normal 50 ms wait remains. Exhaustion must not start another connect.
      time.sleep(min(.05,self._remaining()))
     self._remaining();self.bytes_received=0
     result=self._exchange(op,a,b)
     self._remaining()
     self.last_timing.update(total_request_ms=(time.perf_counter()-begun)*1000,retry_count=attempt,reconnects=self.reconnects)
     return result
    except OSError as error:
     self.close()
     # A socket timeout at the remaining-budget boundary is a total timeout,
     # even if the OS reports the ordinary idle-timeout exception class.
     if self._request_deadline-time.monotonic()<=0 and not isinstance(error,RequestDeadlineExceeded):
      error=RequestDeadlineExceeded('Logical TCP request deadline exceeded during '+self.stage)
     self.failures.append(dict(at=time.time(),op=op,stage=self.stage,bytes_received=self.bytes_received,error=str(error)));self.failures=self.failures[-100:]
     if attempt or isinstance(error,RequestDeadlineExceeded):raise error
     self.reconnects+=1
  finally:self._request_deadline=None
 def _exchange(self,op,a,b=0):
  try:
   if self.sock is None:
    self.stage='connect';self.first_frame=True;self.sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    # Reserve more than one full frame before the SYN negotiates window scaling.
    # A small initial Windows receive buffer can close the window mid-burst.
    self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024)
    self._socket_timeout(2);self.sock.connect((self.address,self.port));self._remaining()
    self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    # Direct gigabit link: normal full-frame payloads take about 50 ms. A lost
    # tail can otherwise wait seconds for TCP retransmission. Restart a stalled
    # read after 350 ms with no incoming bytes; the board retains the same event
    # until a complete, durably saved frame receives an application ACK.
   # A fresh connection needs a longer first-image deadline: hardware tests
   # observed initial TCP recovery exceeding 350 ms. This does not pause PL
   # capture or release queued evidence. Steady-state reads retain the short
   # idle bound; retries start a new connection and may warm up again.
   if op in (1,5) and b&16:
    # A cached peer version may belong to a previous connection/firmware.
    # Probe on this exact socket before EACH low-gate request, including retries.
    # Status neither changes inspection settings nor acknowledges evidence.
    _,_,peer=self._exchange(3,0)
    if peer[0]!=0x54494c33 or peer[1]<LOW_GATE_VERSION:
     raise ValueError('Low product gate requires firmware >= 1.37 on the current connection')
   if op in (1,5) and b&960:
    _,peer_status,peer=self._exchange(3,0)
    if peer[0]!=0x54494c33 or peer[1]<(BOOST_VERSION if b&512 else SUPPORT_VERSION if b&384 else RIDGE_VERSION):
     raise ValueError('Directional/support profile requires compatible candidate firmware on the current connection')
    if b&512 and (peer_status[37]!=BOOST_MODEL_ID or peer_status[38]!=BOOST_MODEL_ID):raise ValueError('FPGA model identity mismatch on the current connection')
    contract=getattr(self,'single_tile_contract',None)
    if contract is not None:
     from single_tile_profile import validate_wire_contract
     _,profile_status,profile_meta=self._exchange(6,0)
     identity=validate_wire_contract(contract,profile_status,profile_meta)
     if identity['boot_id']!=peer[2]:raise ValueError('Board restarted during single-tile preflight')

   self._receive_timeout=2 if op==1 and self.first_frame else self.read_idle_timeout
   started=time.perf_counter()
   self.bytes_received=0;self.stage='send';self._socket_timeout(self._receive_timeout)
   self.sock.sendall(struct.pack('<4I',MAGIC,op,a,b));self.requests_sent+=1;self._remaining()
   self.stage='header';header=self.exact(272);words=struct.unpack('<68I',header)
   magic,code,size,flags=words[:4];codec=flags>>8
   if magic!=MAGIC or code not in (0,1) or flags not in (0,1,3,5,7,15,257,259,263,271,527) or (op==1)!=(code==0):raise ValueError('Invalid TCP protocol header')
   crc_present=bool(flags&2);version=words[45]
   header_crc_present=bool(flags&4)
   if header_crc_present!=(version>=0x10c00):raise ValueError('Header CRC/version mismatch')
   self.stage='header_crc'
   if header_crc_present and struct.unpack('<I',self.exact(4))[0]!=zlib.crc32(header):raise ValueError('Header CRC mismatch; identity not accepted')
   self._remaining()
   received_header=time.perf_counter()
   descriptor_verified=bool(flags&8)
   if code==1 and (size or codec or crc_present or descriptor_verified):raise ValueError('Invalid TCP status payload')
   if code==0 and descriptor_verified!=(version>=0x10e00):raise ValueError('PL descriptor CRC/version mismatch')
   if code==0 and crc_present!=(version>=0x10b00):raise ValueError('Frame CRC/version mismatch')
   if codec==2 and (version<0x11900 or not b&8 or not b&2 or size!=FRAME_BYTES//4*3+FRAME_BYTES//32):raise ValueError('Invalid packed capability/version/length')
   if code==0 and (size>FRAME_BYTES or (codec==0 and size!=FRAME_BYTES) or (codec==1 and (not b&2 or size<8 or size%4))):raise ValueError('Invalid TCP image payload')
   self.stage='payload';payload=self.exact(size) if size else b''
   finished=time.perf_counter()
   self.stage='decode'
   if codec==1:payload=decode_rle(payload,FRAME_BYTES)
   elif codec==2:payload=decode_packed(payload,FRAME_BYTES)
   # CPU work is not preempted. Check after successful decode/CRC before
   # publishing success; malformed data still fails validation without retry.
   self._remaining()
   crc_started=time.perf_counter()
   self.stage='pixel_crc'
   if crc_present and zlib.crc32(payload)!=words[47]:raise ValueError('PL frame CRC mismatch; evidence not acknowledged')
   self._remaining()
   decoded=time.perf_counter()
   self.last_timing=dict(request_ms=(decoded-started)*1000,header_wait_ms=(received_header-started)*1000,payload_ms=(finished-received_header)*1000,payload_MB_s=(size/1e6/(finished-received_header) if size else 0),goodput_MB_s=(size/1e6/(finished-started) if size else 0),decode_ms=(decoded-finished)*1000,wire_payload_bytes=size,uncompressed_bytes=FRAME_BYTES if code==0 else 0,wire_codec={0:'RAW32',1:'WORD_RLE',2:'BGR24_MASK1'}[codec],wire_saving_percent=100*(1-size/FRAME_BYTES) if code==0 else 0)
   if size:self.first_frame=False
   self.last_timing.update(pixel_crc_verified=crc_present,pixel_crc32=(words[47] if crc_present else None),header_crc_verified=header_crc_present,descriptor_crc_verified=descriptor_verified,crc_ms=(decoded-crc_started)*1000 if crc_present else 0,decode_ms=(crc_started-finished)*1000)
   if words[44]==0x54494c33:self.peer_version=version
   self.stage='idle';return payload,list(words[4:44]),list(words[44:])
  except Exception:self.close();raise
 def _support_profile(self,threshold,enhance,passes,wide_weak,ridge,wide_line,directional_growth,pixel_boost=False):
  if type(pixel_boost) is not bool or (pixel_boost and (wide_line or directional_growth or threshold!=90 or not enhance or passes!=4 or not wide_weak or not ridge or self.peer_version<BOOST_VERSION)):raise ValueError('Integer boost requires exclusive 0x13100 profile, T90 and four-pass wide/mean support')
  if type(wide_line) is not bool or type(directional_growth) is not bool:raise ValueError('Invalid support profile flag')
  if wide_line and directional_growth:raise ValueError('Support profiles are mutually exclusive')
  if passes==8 and not directional_growth:raise ValueError('Eight passes require directional growth')
  if wide_line or directional_growth:
   if threshold!=90 or not enhance or not wide_weak or not ridge or passes!=(8 if directional_growth else 4) or self.peer_version<SUPPORT_VERSION:raise ValueError('Fixed support profile requires 0x12d00 candidate firmware and T90 settings')
 def capture(self,threshold,enhance=True,passes=2,low_gate=False,wide_weak=False,ridge=False,wide_line=False,directional_growth=False,pixel_boost=False):
  self._support_profile(threshold,enhance,passes,wide_weak,ridge,wide_line,directional_growth,pixel_boost)
  if type(ridge) is not bool or (ridge and (threshold!=90 or not enhance or passes not in (4,8) or not wide_weak or self.peer_version<RIDGE_VERSION)):raise ValueError('Invalid directional mean profile/version')
  if type(enhance) is not bool or type(passes) is not int or passes not in (2,4,8) or (not enhance and passes!=2) or type(low_gate) is not bool or type(wide_weak) is not bool:raise ValueError('Invalid bounded growth/product gate mode')
  if wide_weak and (not enhance or passes not in (4,8) or self.peer_version<WIDE_WEAK_VERSION):raise ValueError('Wide weak support requires V1.52 firmware and four-pass growth')
  compression=self.compression;packed=self.packed
  capability=8 if compression and packed and self.peer_version>=0x11900 else 0
  t=time.monotonic();raw,d,m=self.exchange(1,threshold,(0 if enhance else 1)|(2 if compression else 0)|(4 if passes in (4,8) else 0)|capability|(16 if low_gate else 0)|(32 if wide_weak else 0)|(64 if ridge else 0)|(128 if wide_line else 0)|(256 if directional_growth else 0)|(512 if pixel_boost else 0));return raw,d,m,round((time.monotonic()-t)*1000)
 def ack(self,boot,event):
  _,_,meta=self.exchange(2,boot,event)
  if meta[0]!=0x54494c33 or meta[2]!=boot or meta[4]!=event:
   self.close();raise ValueError('ACK response identity mismatch; saved evidence retained')
 def configure(self,threshold,enhance=True,passes=2,low_gate=False,wide_weak=False,ridge=False,wide_line=False,directional_growth=False,pixel_boost=False):
  self._support_profile(threshold,enhance,passes,wide_weak,ridge,wide_line,directional_growth,pixel_boost)
  if type(ridge) is not bool or (ridge and (threshold!=90 or not enhance or passes not in (4,8) or not wide_weak or self.peer_version<RIDGE_VERSION)):raise ValueError('Invalid directional mean profile/version')
  if type(threshold) is not int or not 1<=threshold<=255 or type(enhance) is not bool or type(passes) is not int or passes not in (2,4,8) or (not enhance and passes!=2) or type(low_gate) is not bool or type(wide_weak) is not bool:raise ValueError('Invalid inspection parameters')
  if wide_weak and (not enhance or passes not in (4,8) or self.peer_version<WIDE_WEAK_VERSION):raise ValueError('Wide weak support requires V1.52 firmware and four-pass growth')
  self.exchange(5,threshold,(0 if enhance else 1)|(4 if passes in (4,8) else 0)|(16 if low_gate else 0)|(32 if wide_weak else 0)|(64 if ridge else 0)|(128 if wide_line else 0)|(256 if directional_growth else 0)|(512 if pixel_boost else 0))
 def stats(self):
  _,d,m=self.exchange(3,0)
  if m[0]!=0x54494c33:raise ValueError('Invalid board status identity')
  result=dict(zip(META_NAMES,m))
  if m[1]>=0x00010400:
   result.update(products_completed=d[16],defective_products=d[17],current_product_id=d[18],product_flags=d[19],orphaned_products=d[20],best_updates=d[21],dma_max_batch=d[22],tcp_write_failures=d[6],tcp_output_failures=d[7],tcp_connections=d[9],tcp_max_retransmits=d[10],tcp_max_no_progress_ms=d[11],tcp_timeouts=d[12])
  if m[1]>=0x00010800:result['compression_probe_bypasses']=d[39]
  if m[1]>=0x00010e00:result.update(descriptor_crc_errors=d[13],descriptor_verified_frames=d[14],last_descriptor_crc32=d[15])
  if m[1]>=0x11300:result['capture_health']=decode_health(d[:6],m[1])
  if m[1]>=0x11400:result['capture_recovery']=decode_recovery(d[23:37])
  if m[1]>=BOOST_VERSION:result.update(pl_model_id=d[37],expected_model_id=d[38],model_identity_matches=bool(d[37] and d[37]==d[38]))
  return result
 def diagnostics(self):
  _,d,_=self.exchange(4,0)
  return dict(raw=d,reconnects=self.reconnects,recent_failures=list(self.failures))
