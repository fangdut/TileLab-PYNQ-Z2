"""All117 physical payload equality and live corrupt-input transport guards."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,hashlib,struct,zlib,socket,time
import numpy as np
from board_client import Board,exact,ID
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--pause',type=float,default=0);a=p.parse_args()
    if not 0<=a.pause<=10:p.error('--pause must be between0and10seconds')
    a.out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    z=ZipFile(a.bundle/'verified_hdmi/evidence/all117_direct_raw.zip');model=json.loads((a.bundle/'verified_hdmi/model/graph.json').read_text());board=Board(timeout=30);header=board.request(1)[0];assert header[6]==model['crc32'];boot=header[8]
    raw=b'\x01\x02\x03\x00';bad=[0x16905458,5,1990001,4,0,1,1,zlib.crc32(raw)^1,0,0,0,0,0,0,0,0];bad[15]=zlib.crc32(struct.pack('<15I',*bad[:15]))
    with board._connect() as sock:
        sock.settimeout(3);sock.sendall(struct.pack('<16I',*bad)+raw);wire=exact(sock,64);h=struct.unpack('<16I',wire)
        assert h[15]==zlib.crc32(wire[:60]) and h[1]==4 and h[3]==0 and h[5]==ID and h[8]==boot
    guards=dict(corrupt_payload_rejected_before_inference=True)
    bad=[0x16905458,1,1990002,0,0,0,0,0,0,0,0,0,0,0,0,0];bad[15]=zlib.crc32(struct.pack('<15I',*bad[:15]))^1
    with board._connect() as sock:
        sock.settimeout(3);sock.sendall(struct.pack('<16I',*bad))
        try:reply=sock.recv(64)
        except ConnectionResetError:reply=b''
        assert reply==b''
    guards['corrupt_header_rejected']=True;(a.out/'transport_guards.json').write_text(json.dumps(guards,indent=2))
    rows=[(n,json.loads(z.read(n))) for n in z.namelist() if n.endswith('/evidence.json')];assert len(rows)==117
    records=[]
    for i,(name,old) in enumerate(rows):
        if i and a.pause:time.sleep(a.pause)
        ident=name.split('/')[0];path=Path(old['input']);assert hashlib.sha256(path.read_bytes()).hexdigest()==old['input_file_sha256']
        folder=a.out/ident;r=board.infer(path,folder,model);expected=np.frombuffer(z.read(ident+'/raw_result.bin'),dtype='<u4').copy();actual=np.fromfile(folder/'raw_result.bin',dtype='<u4');expected[9]=actual[9]
        assert r['boot_identity']==boot and np.array_equal(expected,actual)
        records.append(dict(id=ident,label=path.parent.name,result=r,raw_exact_except_sequence=True));(a.out/'results.json').write_text(json.dumps(records,indent=2));print('EXACT_ARCHIVE',i+1,'OF117',flush=True)
    summary=dict(scope='PHYSICAL117_EXPOSED_DEVELOPMENT_RAW_REPRODUCTION_NOT_NEW_ACCURACY',cases=117,normal_images=sum(r['label']=='good' for r in records),normal_false_alarms=sum(r['label']=='good' and r['result']['pl_image_alarm']==1 for r in records),defects_detected=sum(r['label']!='good' and r['result']['pl_image_alarm']==1 for r in records),all_scores_masks_meta_exact_except_sequence=True,boot_identity=boot,model_sha256=model['sha256'],mean_engine_seconds=float(np.mean([r['result']['pl_engine_seconds'] for r in records])),mean_transfer_detection_seconds=float(np.mean([r['result']['wall_seconds'] for r in records])),connection_retries=board.connection_retries,transport_guards=guards,cpu_detection=False,gpu_detection=False)
    summary.update(inter_case_pause_seconds=a.pause,batch_wall_seconds=time.monotonic()-started,continuous_video_or_uninterrupted_high_duty_claim=False)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
