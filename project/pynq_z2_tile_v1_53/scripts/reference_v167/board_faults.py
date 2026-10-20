"""Exercise malformed uploads on the actual board, then verify fresh outputs."""
from pathlib import Path
import argparse,sys,json,socket,struct,zlib,time,secrets,hashlib
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'host'));sys.path.insert(0,str(R/'tools/reference_tile'))
from reference_frame_tcp import inspect,exact,MAGIC
from reference_capture import Capture
import frame_v167
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--address',default='192.168.33.10');p.add_argument('--program-proof',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    program=json.loads(a.program_proof.read_text());peer=Capture(a.address);initial=peer.status()
    if initial['boot_id']!=program['boot_id']:raise ValueError('Wrong running deployment')
    rng=np.random.default_rng(1678801);paired=rng.integers(0,1<<56,(500,500),dtype=np.uint64);fit=dict(gain_q8=[320,205,287],offset_integer=[-20,20,-3]);payload=paired.astype('<u8').tobytes();rows=[]
    def header(corrupt=False,gain=320):
        w=[MAGIC,2,secrets.randbelow(0xfffffffe)+1,len(payload),zlib.crc32(payload)^int(corrupt),gain,205,287,(-20)&0xffffffff,20,(-3)&0xffffffff,18,9,0,0];body=struct.pack('<15I',*w);return body+struct.pack('<I',zlib.crc32(body))
    def recovered(name):
        # Only this functional check may retry a transient busy connection
        # after an intentionally abandoned in-flight request. Each attempt
        # recomputes and validates the complete 250000-pixel output.
        for attempt in range(6):
            try:words,proof=inspect(a.address,paired,fit);break
            except OSError:
                if attempt==5:raise
                time.sleep(.1)
        expected=frame_v167.oracle(paired,fit);different=int(np.count_nonzero(words!=expected))
        if different:raise AssertionError('Stale or corrupt FPGA result after '+name)
        rows.append(dict(fault=name,recovered=True,mismatch_pixels=different,proof=proof));print(json.dumps(dict(fault=name,recovered=True)),flush=True)
    for name in ('header_crc','invalid_gain','truncated_upload','payload_crc','abandoned_full_upload'):
        with socket.create_connection((a.address,9134),timeout=5) as s:
            s.settimeout(5);h=bytearray(header(corrupt=name=='payload_crc',gain=0 if name=='invalid_gain' else 320))
            if name=='header_crc':h[-1]^=1
            s.sendall(h)
            if name=='truncated_upload':s.sendall(payload[:1023])
            elif name in ('payload_crc','abandoned_full_upload'):s.sendall(payload)
            if name in ('header_crc','invalid_gain'):
                try:reply=s.recv(64)
                except ConnectionResetError:reply=b''
                if reply:raise AssertionError('Malformed request returned a response')
            if name=='payload_crc':
                raw=exact(s,64);r=struct.unpack('<16I',raw)
                if r[1]!=2 or r[3]!=0 or zlib.crc32(raw[:60])!=r[15]:raise AssertionError('Corrupt payload was not rejected')
        time.sleep(.1);recovered(name)
    final=peer.status()
    if final['boot_id']!=initial['boot_id']:raise AssertionError('Fault test silently rebooted the board')
    result=dict(scope='ACTUAL_BOARD_PROTOCOL_FAULT_RECOVERY_NOT_REAL_TILE_ACCURACY',passed=True,initial=initial,final=final,programming=program,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows)
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
