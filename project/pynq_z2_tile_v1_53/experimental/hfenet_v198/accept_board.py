"""Compare physical PL masks to frozen offline oracles; no host inference."""
from pathlib import Path
import argparse,json,hashlib,time,zlib
import numpy as np
from PIL import Image
from board_client import Board

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    for name in ['model','program','regression','oracle','manifest','gallery','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--board',default='192.168.33.10');a=p.parse_args()
    if a.out.exists():raise ValueError('Fresh evidence output required')
    reg=json.loads((a.regression/'summary.json').read_text());program=json.loads((a.program/'identity.json').read_text())
    assert reg['cases']==80 and reg['all72_tensors_each_image_exact'] and reg['all_masks_exact']
    assert program['build']['pl_identity']==0x19800001 and reg['model_sha256']==program['build']['model_sha256']
    rows=json.loads(a.manifest.read_text())['images'];assert len(rows)==80
    if a.pilot:rows=[next(r for r in rows if r['label']==label) for label in ['good','defect']]
    a.out.mkdir();plan=dict(scope='PHYSICAL_HFENET198_PILOT' if a.pilot else 'PHYSICAL_HFENET198_AUTHOR_DATA_DEVELOPMENT_REGRESSION',cases=len(rows),training=False,independent_validation=False,model_sha256=reg['model_sha256'],program_identity_sha256=sha(a.program/'identity.json'),manifest_sha256=sha(a.manifest),regression_summary_sha256=sha(a.regression/'summary.json'),input_ids=[r['id'] for r in rows],cpu_detection=False,gpu_detection=False)
    (a.out/'plan.json').write_text(json.dumps(plan,indent=2));board=Board(a.board);board.boot=program['boot_identity'];model=board.upload(a.model);records=[];begin=time.monotonic()
    for i,row in enumerate(rows):
        image=a.gallery/row['id']/'original.png';expected=np.load(a.oracle/row['id']/'expected_mask.npy',allow_pickle=False)
        rgb=np.asarray(Image.open(image).convert('RGB'),dtype='u4');packed=((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4').tobytes()
        assert hashlib.sha256(packed).hexdigest()==sha(a.oracle/row['id']/'rgb.bin'),'Original input changed'
        sealed_file_sha=sha(image)
        folder=a.out/row['id'];record=board.infer(image,folder,model);raw=np.fromfile(folder/'raw_result.bin',dtype='<u4')
        assert record['input_file_sha256']==sealed_file_sha and record['rgb_crc32']==zlib.crc32(packed),'Physical request changed from frozen input'
        exact=np.array_equal(raw[17:].reshape(expected.shape),expected);record.update(id=row['id'],label=row['label'],frozen_mask_exact=bool(exact),expected_mask_file_sha256=sha(a.oracle/row['id']/'expected_mask.npy'))
        records.append(record);(a.out/'progress.json').write_text(json.dumps(records,indent=2));assert exact,'Physical PL mask differs from frozen integer oracle'
        print('PHYSICAL_EXACT',i+1,'OF',len(rows),flush=True)
    summary=dict(**plan,completed=len(records),all_masks_exact=True,boot_identity=board.boot,board_verified=True,full80_board_acceptance=not a.pilot,tp=sum(r['label']=='defect' and r['pl_image_alarm']==1 for r in records),fp=sum(r['label']=='good' and r['pl_image_alarm']==1 for r in records),tn=sum(r['label']=='good' and r['pl_image_alarm']==0 for r in records),fn=sum(r['label']=='defect' and r['pl_image_alarm']==0 for r in records),engine_seconds=[r['pl_engine_seconds'] for r in records],wall_seconds=time.monotonic()-begin,limitation='Author model on author development scans; not independent validation, full physical tiles, conveyor actuation or arbitrary painted/material qualification')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
