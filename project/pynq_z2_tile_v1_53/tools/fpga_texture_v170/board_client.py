"""Photo decode/transport/display ONLY. Detection results must come from PL.

No torch/onnx/OpenCV inference, resize, normalization, feature extraction or
host thresholding is present in this application. Pillow decodes and renders.
"""
from pathlib import Path
import argparse,hashlib,json,socket,struct,time,zlib
import numpy as np
from PIL import Image

ID=0x17000001
def exact(sock,n):
    b=bytearray()
    while len(b)<n:
        part=sock.recv(min(262144,n-len(b)))
        if not part:raise ConnectionError('Board disconnected before verified result')
        b.extend(part)
    return bytes(b)

class Board:
    def __init__(self,address='192.168.33.10',port=9136,timeout=120):
        self.address=address;self.port=port;self.timeout=timeout;self.seq=0
    def request(self,op,payload=b'',offset=0,width=0,height=0,identity=0):
        self.seq+=1
        header=[0x16905458,op,self.seq,len(payload),offset,width,height,zlib.crc32(payload) if payload else 0,identity,0,0,0,0,0,0,0]
        header[15]=zlib.crc32(struct.pack('<15I',*header[:15]))
        start=time.perf_counter()
        with socket.create_connection((self.address,self.port),timeout=10) as s:
            s.settimeout(self.timeout);s.sendall(struct.pack('<16I',*header));s.sendall(payload)
            wire=exact(s,64);h=struct.unpack('<16I',wire)
            if h[0]!=0x16905258 or h[2]!=self.seq or h[15]!=zlib.crc32(wire[:60]) or h[5]!=ID:raise RuntimeError('Wrong PL image or corrupt reply header')
            if h[3]>4*(16+56*56+1024*1024):raise RuntimeError('Oversized response')
            data=exact(s,h[3])
        if h[4]!=(zlib.crc32(data) if data else 0):raise RuntimeError('Payload CRC failed')
        if h[1]:raise RuntimeError(f'Board rejected request: status {h[1]}')
        return h,data,time.perf_counter()-start
    def upload(self,model):
        record=json.loads((model/'graph.json').read_text());path=model/'model.bin'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise RuntimeError('Model SHA failed')
        for attempt in range(3):
            try:
                h,_,_=self.request(1);break
            except OSError:
                if attempt==2:raise
                print('Waiting for board Ethernet startup',flush=True);time.sleep(1)
        if h[6]==record['crc32'] and h[7]==record['model_bytes']:
            print('Board already holds the sealed model',flush=True);return record
        self.request(2,offset=record['model_bytes'],identity=record['crc32'])
        pos=0
        with path.open('rb') as f:
            while block:=f.read(1048576):
                h,_,_=self.request(3,block,offset=pos);pos+=len(block)
                if h[7]!=pos:raise RuntimeError('Model upload offset mismatch')
                if pos%10485760==0 or pos==record['model_bytes']:print(f'Model uploaded {pos}/{record["model_bytes"]}',flush=True)
        h,_,_=self.request(4)
        if h[6]!=record['crc32']:raise RuntimeError('Model commit CRC failed')
        return record
    def infer(self,path,output,model):
        with Image.open(path) as image:rgb=np.asarray(image.convert('RGB'),dtype=np.uint32)
        height,width=rgb.shape[:2]
        if not(1<=width<=1024 and 1<=height<=1024):raise ValueError('Input must be at most 1024x1024; no CPU resize fallback')
        packed=((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4').tobytes()
        h,data,wall=self.request(5,packed,width=width,height=height)
        if h[6]!=model['crc32'] or h[12]!=zlib.crc32(packed) or (h[13],h[14])!=(width,height):raise RuntimeError('Evidence does not match this photo/model')
        result=np.frombuffer(data,dtype='<u4');meta=result[:16]
        if len(result)!=16+model['grid']*model['grid']+width*height or meta[0]!=ID or meta[1]!=0 or meta[5]!=model['grid'] or meta[7]!=width*height or meta[8]!=model['steps']:raise RuntimeError('Incomplete PL graph result')
        scores=result[16:16+model['grid']*model['grid']].astype('<i4').reshape(model['grid'],model['grid'])
        mask=result[16+model['grid']*model['grid']:].reshape(height,width)
        if np.any(mask>1) or int(mask.sum())!=int(meta[6]):raise RuntimeError('PL mask consistency failed')
        output.mkdir(parents=True,exist_ok=False)
        (output/'raw_result.bin').write_bytes(data);np.save(output/'scores.npy',scores);Image.fromarray((mask*255).astype('uint8')).save(output/'mask.png')
        original=rgb.astype('uint8');overlay=original.copy();selected=mask.astype(bool)
        overlay[selected]=(0.5*overlay[selected]+np.array([127.5,0,0])).astype('uint8')
        Image.fromarray(overlay).save(output/'overlay.png');Image.fromarray(original).save(output/'input.png')
        score,threshold=meta[3:5]
        record=dict(scope='BOARD_FULL_PL_INFERENCE',input=str(path.resolve()),input_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            rgb_crc32=h[12],model_sha256=model['sha256'],model_crc32=h[6],pl_identity=h[5],boot_identity=h[8],
            width=width,height=height,pl_image_alarm=int(meta[2]),pl_peak=float(score),pl_threshold=float(threshold),
            pl_mask_pixels=int(meta[6]),pl_completed_steps=int(meta[8]),pl_frame_sequence=int(meta[9]),ps_global_timer_ticks=h[9]+(h[10]<<32),ps_timer_hz=h[11],pl_engine_seconds=(h[9]+(h[10]<<32))/h[11] if h[11] else None,wall_seconds=wall,
            result_crc32=h[4],result_sha256=hashlib.sha256(data).hexdigest(),reply_header=list(h),cpu_detection=False,gpu_detection=False)
        (output/'evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(record,ensure_ascii=False),flush=True);return record
    def auto_benchmark(self,frames,model,last_photo,output):
        h,data,wall=self.request(6,offset=frames);words=struct.unpack('<16I',data)
        if words[0]!=0x1700b001 or words[1]!=frames or words[2]<frames or words[2]>frames+2:raise RuntimeError('Invalid PL auto-restart completion count')
        if (words[4]-words[3])&0xffffffff!=words[2] or words[5]!=last_photo['rgb_crc32'] or words[6]!=model['crc32'] or h[8]!=last_photo['boot_identity']:raise RuntimeError('Auto-restart source/model/boot mismatch')
        seconds=(h[9]+(h[10]<<32))/h[11]
        record=dict(scope='PHYSICAL_PL_AUTORESTART_FIXED_FRAME_MICROBENCHMARK',frames=words[2],requested=frames,
            first_sequence=words[3],last_sequence=words[4],elapsed_engine_seconds=seconds,sustained_pl_fps=words[2]/seconds,
            wall_seconds=wall,arm_start_writes=1,hardware_auto_restart=True,new_video_frames=False,
            model_sha256=model['sha256'],source_rgb_crc32=words[5],boot_identity=h[8],pl_identity=h[5],
            cpu_detection=False,gpu_detection=False,limitation='Repeated fixed DDR frame; not continuous HDMI/video end-to-end throughput')
        output.write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record),flush=True);return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--board',default='192.168.33.10');p.add_argument('--model',type=Path,required=True);p.add_argument('--image',type=Path);p.add_argument('--out',type=Path);p.add_argument('--status',action='store_true');a=p.parse_args()
    board=Board(a.board)
    if a.status:print(board.request(1)[0]);return
    model=board.upload(a.model)
    if a.image:
        if not a.out:p.error('--out required with --image')
        board.infer(a.image,a.out,model)
if __name__=='__main__':main()
