"""V167 capture-only client. A zero capture mask is not an inspection result."""
import socket,struct,zlib,time
from reference_frame_tcp import exact
from workstation import Bridge
MAGIC=0x544c5033
class Capture:
    def __init__(self,address):self.address=address
    def request(self,op,a=0,b=0):
        started=time.perf_counter();deadline=time.monotonic()+5
        with socket.create_connection((self.address,9133),timeout=5) as s:
            s.settimeout(5);s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024)
            s.sendall(struct.pack('<4I',MAGIC,op,a,b));h=exact(s,276,deadline);w=struct.unpack('<69I',h)
            if w[0]!=MAGIC or w[68]!=zlib.crc32(h[:272]) or w[44]!=0x54494c33 or w[45]!=0x16700 or not w[46]:raise ValueError('V167 capture identity/header CRC mismatch')
            if op==7:
                if w[1:4]!=(0,3686400,15):raise ValueError('Unexpected raw capture packet')
                payload=exact(s,w[2],deadline)
                if zlib.crc32(payload)!=w[47]:raise ValueError('Captured pixel CRC mismatch')
                frame,png,mask=Bridge.decode_event(payload,list(w[4:44]),list(w[44:68]),(time.perf_counter()-started)*1000)
                if any(payload[3::4]) or frame['alarm'] or frame['boxes']:raise ValueError('Capture-only image must not contain a legacy detection result')
                frame.update(pixel_crc_verified=True,header_crc_verified=True,descriptor_crc_verified=True,pixel_crc32=w[47],capture_scope='V167_CAPTURE_ONLY_NOT_INSPECTION',algorithm='RAW_HDMI_CAPTURE_ONLY',transport='ETHERNET_TCP',region_evidence_enabled=False,region_min_trusted=None,region_evidence_fraction=None,support_profile=None)
                return frame,png,mask
            if w[1]!=1 or w[2]!=0:raise ValueError('Board control rejected')
            return list(w[4:44]),list(w[44:68])
    def status(self):
        d,m=self.request(6)
        if d[:7]!=[0x16700601,0x006e0186,0x02610379,0x16700601,500,0x16700,1]:raise ValueError('V167 capture ROI/profile mismatch')
        return dict(boot_id=m[2],firmware=m[1],pl_id=d[3])
    def capture(self):
        peer=self.status();frame,image,mask=self.request(7,0x16700601)
        if frame['boot_id']!=peer['boot_id']:raise ValueError('Board restarted during capture')
        return frame,image,mask
    def ack(self,frame):
        d,m=self.request(2,frame['boot_id'],frame['event_id'])
        if m[2]!=frame['boot_id']:raise ValueError('Board restarted before durable capture ACK')
