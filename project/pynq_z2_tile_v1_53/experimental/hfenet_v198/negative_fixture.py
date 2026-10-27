"""Synthetic second-frame mutation, not a new photo accuracy sample."""
from pathlib import Path
import argparse,shutil,json,struct,hashlib,zlib
import numpy as np
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();meta=json.loads((a.base/'graph.json').read_text());assert meta['synthetic_weights'] and meta['retained_fixture'];a.out.mkdir(exist_ok=False)
    blob=bytearray((a.base/'model.bin').read_bytes());h=struct.unpack_from('<64I',blob);last=None
    for i in range(h[2]):
        op=struct.unpack_from('<32I',blob,(h[19]+32*i)*4)
        if op[0]==2:last=op
    assert last is not None and last[13]==1 and last[6:8]==(1,1)
    for k in range(last[15]):
        offset=(last[5]+k)*2;v=struct.unpack_from('<h',blob,offset)[0];assert v>=0;struct.pack_into('<h',blob,offset,-v)
    (a.out/'model.bin').write_bytes(blob);meta.update(sha256=hashlib.sha256(blob).hexdigest(),crc32=zlib.crc32(blob),synthetic_negative_final=True);(a.out/'graph.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
    for name in ['allocation.json','gold_metadata.json']:shutil.copy2(a.base/name,a.out/name)
    data={k:v for k,v in np.load(a.base/'gold_weights.npz',allow_pickle=False).items()};gold=json.loads((a.base/'gold_metadata.json').read_text());conv=[o for o in gold['source']['operators'] if o['kind']=='conv2d_int16_mac48'][-1];data[conv['name']]=-data[conv['name']];np.savez_compressed(a.out/'gold_weights.npz',**data)
    print(json.dumps(dict(model=str(a.out),sha256=meta['sha256'])))
if __name__=='__main__':main()
