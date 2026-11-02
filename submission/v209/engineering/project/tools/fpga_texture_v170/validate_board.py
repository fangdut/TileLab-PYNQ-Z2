"""Physical FPGA integer benchmark. Test labels only evaluate frozen outputs."""
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
from board_client import Board

def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def mask_ref(s,w,h,threshold):
    g=s.shape[0];xd=2*w;yd=2*h;xx=np.clip((2*np.arange(w)+1)*g-w,0,(g-1)*xd);yy=np.clip((2*np.arange(h)+1)*g-h,0,(g-1)*yd)
    x0=xx//xd;y0=yy//yd;x1=np.minimum(x0+1,g-1);y1=np.minimum(y0+1,g-1);fx=xx%xd;fy=yy%yd;s=s.astype('i8')
    a=s[y0[:,None],x0[None,:]]*(xd-fx)[None,:]+s[y0[:,None],x1[None,:]]*fx[None,:]
    b=s[y1[:,None],x0[None,:]]*(xd-fx)[None,:]+s[y1[:,None],x1[None,:]]*fx[None,:]
    return a*(yd-fy)[:,None]+b*fy[:,None]>threshold*xd*yd

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--program',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--board',default='192.168.33.10');p.add_argument('--limit',type=int,default=117);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);manifest=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))
    rows=[r for r in manifest['images'] if r['role']=='test'][:a.limit];program=json.loads((a.program/'identity.json').read_text())
    save(a.out/'plan.json',dict(scope='PHYSICAL_V170_FULL_INTEGER_PL',selected_before_inference=[r['id'] for r in rows],
        benchmark_is_blind=False,programmed_build=program,threshold_adaptation=False))
    board=Board(a.board);model=board.upload(a.profile);results=[];start=time.perf_counter();last=None;last_sequence=None
    for i,r in enumerate(rows):
        image=a.dataset/r['file']
        if hashlib.sha256(image.read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Input provenance mismatch')
        folder=a.out/r['id'];print(f'Physical PL image {i+1}/{len(rows)} {r["label"]}',flush=True)
        e=board.infer(image,folder,model);last=e
        if e['boot_identity']!=program['boot_identity'] or e['model_sha256']!=program['build']['model_sha256']:raise RuntimeError('Program identity mismatch')
        if last_sequence is not None and e['pl_frame_sequence']!=last_sequence+1:raise RuntimeError('Unexpected PL completion sequence')
        last_sequence=e['pl_frame_sequence'];expected=np.load(a.profile/(r['id']+'_scores.npy'),allow_pickle=False)
        actual=np.load(folder/'scores.npy',allow_pickle=False);error=int(np.abs(actual.astype('i8')-expected).max())
        wire=np.fromfile(folder/'raw_result.bin',dtype='<u4');mask=wire[16+model['grid']**2:].reshape(e['height'],e['width'])
        mismatches=int(np.count_nonzero(mask!=mask_ref(expected,e['width'],e['height'],model['threshold'])))
        if error or mismatches:raise RuntimeError(f'Integer FPGA mismatch {r["id"]}: grid={error} mask={mismatches}')
        result=dict(id=r['id'],label=r['label'],alarm=e['pl_image_alarm'],correct=bool(e['pl_image_alarm'])==(r['label']!='good'),
            max_grid_error=error,mask_mismatches=mismatches,engine_seconds=e['pl_engine_seconds'],request_wall_seconds=e['wall_seconds'],frame_sequence=last_sequence)
        results.append(result);save(a.out/'progress.json',results)
    seconds=np.array([r['engine_seconds'] for r in results]);normal=[r for r in results if r['label']=='good'];anomaly=[r for r in results if r['label']!='good']
    summary=dict(scope='PHYSICAL_V170_FULL_INTEGER_PL',cases=len(results),all_integer_outputs_exact=True,
        correct=sum(r['correct'] for r in results),anomalies_detected=sum(r['alarm'] for r in anomaly),anomalies=len(anomaly),
        normal_false_alarms=sum(r['alarm'] for r in normal),normal_images=len(normal),
        cracks_detected=sum(r['alarm'] for r in results if r['label']=='crack'),
        engine_mean_seconds=float(seconds.mean()),engine_p95_seconds=float(np.quantile(seconds,.95)),
        inverse_mean_engine_fps=float(1/seconds.mean()),validation_wall_seconds=time.perf_counter()-start,
        benchmark_is_blind=False,continuous_video_verified=False,cpu_detection=False,gpu_detection=False)
    save(a.out/'summary.json',summary)
    repeats=max(4,min(32,int(10/float(seconds.mean()))))
    auto=board.auto_benchmark(repeats,model,last,a.out/'autorestart_benchmark.json')
    summary['autorestart_fixed_frame_fps']=auto['sustained_pl_fps'];save(a.out/'summary.json',summary)
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
