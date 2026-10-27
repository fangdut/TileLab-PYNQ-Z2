"""HFENet198 photo decode/transport/display, with no host detection fallback."""
from pathlib import Path
import argparse,hashlib,json,socket,struct,time,zlib
import numpy as np
from PIL import Image
if __package__:
    from .model_identity import load_identity
else:
    from model_identity import load_identity

ID=0x19800001
def exact(sock,n):
    data=bytearray()
    while len(data)<n:
        part=sock.recv(min(262144,n-len(data)))
        if not part:raise ConnectionError('Disconnected before complete verified result')
        data.extend(part)
    return bytes(data)

class Board:
    def __init__(self,address='192.168.33.10',port=9136,timeout=1800):
        self.address=address;self.port=port;self.timeout=timeout;self.seq=0;self.boot=None;self.frame=None
    def request(self,op,payload=b'',offset=0,width=0,height=0,identity=0):
        if op not in range(1,6):raise ValueError('Only stop/inspect transport operations 1..5')
        self.seq+=1;crc=zlib.crc32(payload) if payload else 0
        h=[0x16905458,op,self.seq,len(payload),offset,width,height,crc,identity,0,0,0,0,0,0,0]
        h[15]=zlib.crc32(struct.pack('<15I',*h[:15]));start=time.perf_counter()
        with socket.create_connection((self.address,self.port),timeout=10) as sock:
            sock.settimeout(self.timeout);sock.sendall(struct.pack('<16I',*h));sock.sendall(payload)
            wire=exact(sock,64);r=struct.unpack('<16I',wire)
            if r[0]!=0x16905258 or r[2]!=self.seq or r[5]!=ID or r[15]!=zlib.crc32(wire[:60]):raise RuntimeError('Reply header/PL identity invalid')
            if not r[8] or (self.boot is not None and r[8]!=self.boot):raise RuntimeError('Board rebooted; hold product and restart acceptance')
            if r[3]>4*(17+256*1408):raise RuntimeError('Oversized response rejected')
            data=exact(sock,r[3])
        if r[4]!=(zlib.crc32(data) if data else 0):raise RuntimeError('Result CRC invalid')
        if r[1]:raise RuntimeError(f'Board rejected operation: status={r[1]}')
        self.boot=r[8]
        return r,data,time.perf_counter()-start
    def upload(self,profile):
        g,_=load_identity(profile);blob=(profile/'model.bin').read_bytes();r,data,_=self.request(1)
        if data:raise RuntimeError('Unexpected status payload')
        if (r[6],r[7])!=(g['crc32'],g['model_bytes']):
            self.request(2,offset=g['model_bytes'],identity=g['crc32'])
            for pos in range(0,len(blob),1048576):
                block=blob[pos:pos+1048576];r,_,_=self.request(3,block,offset=pos)
                if r[7]!=pos+len(block):raise RuntimeError('Upload position mismatch')
            r,_,_=self.request(4)
        if (r[6],r[7])!=(g['crc32'],g['model_bytes']):raise RuntimeError('Model not sealed on board')
        return g
    def infer(self,path,output,model):
        with Image.open(path) as image:rgb=np.asarray(image.convert('RGB'),dtype=np.uint32)
        height,width=rgb.shape[:2]
        if (width,height)!=(model['width'],model['height']):raise ValueError('Original sealed geometry required; no CPU resize/crop')
        packed=((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4').tobytes()
        h,data,wall=self.request(5,packed,width=width,height=height)
        if h[6]!=model['crc32'] or h[12]!=zlib.crc32(packed) or (h[13],h[14])!=(width,height):raise RuntimeError('Input/model evidence mismatch')
        result=np.frombuffer(data,dtype='<u4');meta=result[:16]
        if len(result)!=17+width*height or tuple(map(int,meta[[0,1,4,5,7,8]]))!=(ID,0,0,1,width*height,71):raise RuntimeError('Incomplete PL network result')
        if np.any(meta[10:16]) or not meta[9]:raise RuntimeError('Invalid PL completion metadata')
        if self.frame is not None and int(meta[9])!=((self.frame+1)&0xffffffff):raise RuntimeError('PL frame sequence skipped/replayed')
        mask=result[17:].reshape(height,width);count=int(mask.sum())
        # Integrity checking of the PL result, never a host decision fallback.
        if np.any(mask>1) or count!=int(meta[3]) or count!=int(meta[6]) or count!=int(result[16]) or int(meta[2])!=int(count>0):raise RuntimeError('PL score/mask/alarm inconsistent')
        self.frame=int(meta[9]);output.mkdir(parents=True,exist_ok=False)
        (output/'raw_result.bin').write_bytes(data);Image.fromarray((mask*255).astype('uint8')).save(output/'mask.png')
        original=rgb.astype('uint8');overlay=original.copy();selected=mask.astype(bool)
        overlay[selected]=(overlay[selected]*.5+np.array([127.5,0,0])).astype('uint8')
        Image.fromarray(original).save(output/'input.png');Image.fromarray(overlay).save(output/'overlay.png')
        record=dict(scope='HFENET198_PHYSICAL_BOARD_FULL_PL_INFERENCE',input=str(path.resolve()),input_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rgb_crc32=h[12],model_sha256=model['sha256'],model_crc32=h[6],pl_identity=h[5],boot_identity=h[8],width=width,height=height,pl_image_alarm=int(meta[2]),pl_mask_pixels=count,pl_completed_steps=int(meta[8]),pl_frame_sequence=self.frame,ps_global_timer_ticks=h[9]+(h[10]<<32),ps_timer_hz=h[11],pl_engine_seconds=(h[9]+(h[10]<<32))/h[11] if h[11] else None,wall_seconds=wall,result_crc32=h[4],result_sha256=hashlib.sha256(data).hexdigest(),reply_header=list(h),cpu_detection=False,gpu_detection=False)
        record.update(pl_peak=int(meta[3]),pl_threshold=int(meta[4]))
        (output/'evidence.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record),flush=True);return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--board',default='192.168.33.10');p.add_argument('--model',type=Path,required=True);p.add_argument('--image',type=Path);p.add_argument('--out',type=Path);p.add_argument('--status',action='store_true');a=p.parse_args();board=Board(a.board)
    if a.status:print(board.request(1)[0])
    else:
        model=board.upload(a.model)
        if a.image:
            if not a.out:p.error('--out required')
            board.infer(a.image,a.out,model)
