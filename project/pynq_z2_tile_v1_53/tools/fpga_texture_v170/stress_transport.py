"""Read-only TCP control stress after video has stopped; never a detector FPS test."""
from pathlib import Path
import argparse,hashlib,json,time
from board_client import Board

def main():
    p=argparse.ArgumentParser()
    for n in ['program','profile','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--queries',type=int,default=300);a=p.parse_args()
    if not 1<=a.queries<=10000:raise ValueError('Query count out of range')
    identity=json.loads((a.program/'identity.json').read_text())
    graph=json.loads((a.profile/'graph.json').read_text())
    digest=hashlib.sha256((a.profile/'model.bin').read_bytes()).hexdigest()
    if digest!=graph['sha256'] or digest!=identity['build']['model_sha256']:raise ValueError('Model provenance mismatch')
    a.out.mkdir(parents=True,exist_ok=False);board=Board();times=[];started=time.perf_counter()
    report=dict(scope='READ_ONLY_TCP_CONTROL_STRESS_AFTER_VIDEO_NOT_DETECTION_SPEED',requested=a.queries,
        completed=0,boot_identity=identity['boot_identity'],model_sha256=digest,
        pl_start_writes=0,model_transfer_writes=0,cpu_detection=False,gpu_detection=False)
    try:
        for i in range(a.queries):
            header,data,wall=board.request(1)
            if data or header[5]!=0x17000001 or header[8]!=identity['boot_identity'] or header[6]!=graph['crc32']:
                raise ValueError('Transport identity changed')
            times.append(wall);report['completed']=i+1
        report['status']='PASS'
    except Exception as error:
        report.update(status='FAILED',error=str(error));raise
    finally:
        report.update(elapsed_seconds=time.perf_counter()-started,max_roundtrip_seconds=max(times,default=None))
        (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
