"""Seal fixed fixture ROI into a separate model profile; no image processing.

Requires the ROI-capable PL build. The accepted full-frame model is untouched.
Changing this header changes the actual CRC and requires matching transport ELF.
"""
from pathlib import Path
import argparse,hashlib,json,struct,zlib,shutil
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--roi',type=int,nargs=4,required=True,metavar=('X','Y','W','H'));p.add_argument('--source-size',type=int,nargs=2,required=True,metavar=('WIDTH','HEIGHT'))
    a=p.parse_args();x,y,w,h=a.roi;sw,sh=a.source_size
    if not (1<=sw<=1024 and 1<=sh<=1024 and x>=0 and y>=0 and w>0 and h>0 and x+w<=sw and y+h<=sh):raise ValueError('Invalid fixed ROI')
    raw=bytearray((a.base/'model.bin').read_bytes());original=bytes(raw);graph=json.loads((a.base/'graph.json').read_text(encoding='utf8'))
    if hashlib.sha256(raw).hexdigest()!=graph['sha256']:raise ValueError('Base model identity mismatch')
    if any(struct.unpack_from('<7I',raw,80)):raise ValueError('Base already has reserved ROI parameters')
    struct.pack_into('<7I',raw,80,x,y,w,h,sw,sh,0x19600001)
    assert raw[:80]==original[:80] and raw[108:]==original[108:]
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'model.bin').write_bytes(raw)
    graph.update(sha256=hashlib.sha256(raw).hexdigest(),crc32=zlib.crc32(raw),input_roi=dict(x=x,y=y,width=w,height=h,source_width=sw,source_height=sh),
        roi_semantics='Fixed operator-calibrated complete-object inspection area; no automatic localization',
        base_model_sha256=hashlib.sha256(original).hexdigest(),requires_roi_capable_pl=True,board_verified=False)
    (a.out/'graph.json').write_text(json.dumps(graph,indent=2),encoding='utf8')
    for file in a.base.glob('*_scores.npy'):shutil.copy2(file,a.out/file.name)
    print(json.dumps(dict(sha256=graph['sha256'],crc32=graph['crc32'],input_roi=graph['input_roi'])))
if __name__=='__main__':main()
