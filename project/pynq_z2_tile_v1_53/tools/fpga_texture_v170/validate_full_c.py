"""Offline full-real-photo HLS C++ arithmetic regression, not FPGA FPS."""
from pathlib import Path
import argparse,json,subprocess,time
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
from PIL import Image
from evaluate_lightweight import sha,save

def mask_reference(scores,width,height,threshold):
    g=scores.shape[0];xd=2*width;yd=2*height
    xx=np.clip((2*np.arange(width)+1)*g-width,0,(g-1)*xd);yy=np.clip((2*np.arange(height)+1)*g-height,0,(g-1)*yd)
    x0=xx//xd;y0=yy//yd;x1=np.minimum(x0+1,g-1);y1=np.minimum(y0+1,g-1);fx=xx%xd;fy=yy%yd;s=scores.astype('i8')
    top=s[y0[:,None],x0[None,:]]*(xd-fx)[None,:]+s[y0[:,None],x1[None,:]]*fx[None,:]
    bottom=s[y1[:,None],x0[None,:]]*(xd-fx)[None,:]+s[y1[:,None],x1[None,:]]*fx[None,:]
    return top*(yd-fy)[:,None]+bottom*fy[:,None]>threshold*xd*yd

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--compiled-check',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--resume',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=a.resume);data=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))
    rows=[r for r in data['images'] if r['role']=='test'];graph=json.loads((a.profile/'graph.json').read_text(encoding='utf8'))
    source=a.compiled_check/'kernel.cpp';exe=a.compiled_check/'check.exe';started=time.perf_counter();results=[];reused=set()
    plan=dict(scope='OFFLINE_HLS_C_ALL_117_NOT_BOARD',ids=[r['id'] for r in rows],source_sha256=sha(source),model_sha256=sha(a.profile/'model.bin'))
    if a.resume and json.loads((a.out/'plan.json').read_text())!=plan:raise ValueError('Resume source/model/case plan differs')
    save(a.out/'plan.json',plan)
    def run(r):
        case=a.out/r['id'];case.mkdir(exist_ok=a.resume);im=a.dataset/r['file']
        with Image.open(im) as image:rgb=np.array(image.convert('RGB'),dtype='<u4')
        h,w=rgb.shape[:2];((rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2]).astype('<u4').tofile(case/'input.bin')
        previous=case/'check.json'
        reuse=False
        if a.resume and previous.exists() and (case/'result.bin').exists():
            proof=json.loads(previous.read_text())
            reuse=proof['id']==r['id'] and proof['result_sha256']==sha(case/'result.bin')
        if reuse:reused.add(r['id'])
        if not reuse:
            with (case/'c.log').open('w') as log:
                subprocess.run([str(exe),str(a.profile/'model.bin'),str(case/'input.bin'),str(case/'result.bin'),str(w),str(h)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        out=np.fromfile(case/'result.bin',dtype='<u4');g=int(out[5]);scores=out[16:16+g*g].reshape(g,g);expected=np.load(a.profile/(r['id']+'_scores.npy'))
        error=int(np.abs(scores.astype('i8')-expected).max());mask=out[16+g*g:].reshape(h,w);reference=mask_reference(expected,w,h,graph['threshold'])
        mismatches=int(np.count_nonzero(mask!=reference));correct=bool(out[2])==(r['label']!='good')
        if error or mismatches or out[1] or out[8]!=graph['steps']:raise RuntimeError(f'Full C mismatch {r["id"]}: grid={error} mask={mismatches}')
        record=dict(id=r['id'],label=r['label'],grid_error=error,mask_mismatches=mismatches,alarm=int(out[2]),peak=int(out[3]),ground_truth_correct=correct,result_sha256=sha(case/'result.bin'))
        save(case/'check.json',record);return record
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        tasks=[pool.submit(run,r) for r in rows]
        for future in as_completed(tasks):
            results.append(future.result());print(f'Full HLS integer C exact {len(results)}/117',flush=True)
            save(a.out/'progress.json',results)
    results.sort(key=lambda r:r['id']);save(a.out/'results.json',results)
    summary=dict(scope='OFFLINE_HLS_C_ALL_117_NOT_BOARD',cases=len(results),all_grid_values_exact=True,all_original_size_masks_exact=True,
        correct=sum(r['ground_truth_correct'] for r in results),source_sha256=sha(source),model_sha256=sha(a.profile/'model.bin'),elapsed_seconds=time.perf_counter()-started,
        resumed=a.resume,revalidated_saved_results=len(reused),elapsed_scope='current invocation only; excludes prior interrupted work; not FPGA speed')
    save(a.out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
