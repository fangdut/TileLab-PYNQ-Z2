"""Physical inference against a pre-frozen manifest. No host vision inference."""
from pathlib import Path
import argparse,json,hashlib,time
from board_client import Board

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--role',choices=['diagnostic','calibration','reserved_final'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((a.dataset/'manifest.json').read_text());model=json.loads((a.profile/'graph.json').read_text())
    assert hashlib.sha256((a.profile/'model.bin').read_bytes()).hexdigest()==model['sha256']
    rows=[r for r in manifest['images'] if r['role']==a.role]
    for r in rows:assert hashlib.sha256((a.dataset/r['file']).read_bytes()).hexdigest()==r['prepared_sha256']
    board=Board(timeout=30);header=board.request(1)[0]
    assert header[6]==model['crc32'] and header[7]==model['model_bytes']
    boot=header[8];records=[];started=time.monotonic()
    (a.out/'plan.json').write_text(json.dumps(dict(role=a.role,model_sha256=model['sha256'],dataset_manifest_sha256=hashlib.sha256((a.dataset/'manifest.json').read_bytes()).hexdigest(),boot_identity=boot,ids=[r['id'] for r in rows]),indent=2))
    for i,r in enumerate(rows):
        result=board.infer(a.dataset/r['file'],a.out/r['id'],model)
        assert result['boot_identity']==boot
        records.append(dict(id=r['id'],label=r['label'],role=a.role,result=result))
        (a.out/'results.json').write_text(json.dumps(records,indent=2));print('PHYSICAL_AUDIT',a.role,i+1,'OF',len(rows),flush=True)
    tp=sum(r['label']!='good' and r['result']['pl_image_alarm']==1 for r in records);fp=sum(r['label']=='good' and r['result']['pl_image_alarm']==1 for r in records)
    n=sum(r['label']=='good' for r in records);d=len(records)-n
    summary=dict(scope='PUBLIC_ROOF_CERAMIC_FILE_HOLDOUT_NOT_INDEPENDENT_SPECIMEN_OR_FLOOR_ACCEPTANCE',role=a.role,cases=len(records),tp=tp,fp=fp,tn=n-fp,fn=d-tp,normal_images=n,defect_images=d,model_sha256=model['sha256'],boot_identity=boot,mean_engine_seconds=sum(r['result']['pl_engine_seconds'] for r in records)/len(records),mean_transfer_detection_seconds=sum(r['result']['wall_seconds'] for r in records)/len(records),wall_seconds=time.monotonic()-started,connection_retries=board.connection_retries,cpu_detection=False,gpu_detection=False,physical_specimen_independence=False)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
