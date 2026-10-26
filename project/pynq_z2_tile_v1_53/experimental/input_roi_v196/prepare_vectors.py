"""Translate frozen fixture into a synthetic surround: arithmetic proof only."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    original=np.fromfile(a.base/'test_rgb.bin',dtype='<u4').reshape(65,79)
    model=bytearray((a.base/'test_model.bin').read_bytes());header=np.frombuffer(model,dtype='<u4')
    width,height,x,y=95,81,7,9;header[20:27]=[x,y,79,65,width,height,0x19600001]
    (a.out/'test_model.bin').write_bytes(model)
    yy,xx=np.indices((height,width));pixels=(((xx*31+yy*11)&255)<<16)|(((xx*13+yy*7)&255)<<8)|((xx*3+yy*29)&255)
    pixels[y:y+65,x:x+79]=original;pixels.astype('<u4').tofile(a.out/'test_rgb.bin')
    old=np.fromfile(a.base/'test_expected.bin',dtype='<u4');g=int(header[4]);end=16+g*g
    new=np.zeros(end+width*height,dtype='<u4');new[:end]=old[:end];new[7]=width*height;new[10:16]=[x,y,79,65,width,height]
    new[end:].reshape(height,width)[y:y+65,x:x+79]=old[end:].reshape(65,79);new.tofile(a.out/'test_expected.bin')
    for name in ['test_fa_expected.bin','test_fb_expected.bin']:(a.out/name).write_bytes((a.base/name).read_bytes())
    proof=dict(scope='SYNTHETIC_SURROUND_AROUND_FROZEN_ARITHMETIC_FIXTURE_NOT_REAL_PHOTO_ACCURACY',roi=[x,y,79,65],source=[width,height],
        expected_features_and_scores='byte-identical to frozen original79x65 fixture',expected_mask='translated within full source; zero outsideROI',
        baseline_fixture={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.base.glob('test*.bin')})
    (a.out/'proof.json').write_text(json.dumps(proof,indent=2),encoding='utf8');print(json.dumps(proof))
if __name__=='__main__':main()
