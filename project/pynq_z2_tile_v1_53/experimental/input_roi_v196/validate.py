"""C/physical ROI engineering check; never a new real-photo accuracy claim."""
from pathlib import Path
import argparse,json,sys,hashlib,subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/fpga_texture_v170'))
from board_client import Board
from validate_board import mask_ref
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['c','board'],required=True)
    for name in ['fixtures','profile','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--compiled',type=Path);p.add_argument('--program',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False)
    graph=json.loads((a.profile/'graph.json').read_text(encoding='utf8'));roi=graph['input_roi'];plan=json.loads((a.fixtures/'plan.json').read_text(encoding='utf8'))
    def save(name,obj):(a.out/name).write_text(json.dumps(obj,indent=2),encoding='utf8')
    identity=json.loads((a.program/'identity.json').read_text(encoding='utf8')) if a.mode=='board' else None
    save('plan.json',dict(mode=a.mode,scope=plan['scope'],fixture_plan_sha256=sha(a.fixtures/'plan.json'),profile_sha256=sha(a.profile/'model.bin'),
        source_sha256=sha(a.compiled/'kernel.cpp') if a.compiled else None,program=identity))
    board=Board() if a.mode=='board' else None
    if board:model=board.upload(a.profile)
    def run(row):
        file=a.fixtures/row['file'];assert sha(file)==row['sha256'];folder=a.out/row['id'];e=None
        if a.mode=='c':
            folder.mkdir();image=np.asarray(Image.open(file).convert('RGB'),dtype=np.uint32);h,w=image.shape[:2]
            ((image[:,:,0]<<16)|(image[:,:,1]<<8)|image[:,:,2]).astype('<u4').tofile(folder/'input.bin')
            with (folder/'c.log').open('w') as log:subprocess.run([str(a.compiled/'check.exe'),str(a.profile/'model.bin'),str(folder/'input.bin'),str(folder/'raw_result.bin'),str(w),str(h)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        else:
            e=board.infer(file,folder,model);assert e['boot_identity']==identity['boot_identity'] and e['model_sha256']==identity['build']['model_sha256']
        wire=np.fromfile(folder/'raw_result.bin',dtype='<u4');g=graph['grid'];header=wire[:16];scores=wire[16:16+g*g].astype('i4').reshape(g,g)
        expected=np.load(a.profile/(row['parent_id']+'_scores.npy'),allow_pickle=False)
        error=int(np.abs(scores.astype('i8')-expected).max());mask=wire[16+g*g:].reshape(roi['source_height'],roi['source_width'])
        reference=np.zeros(mask.shape,dtype='u4');x,y,w,h=[roi[k] for k in ['x','y','width','height']]
        reference[y:y+h,x:x+w]=mask_ref(expected,w,h,graph['threshold']);mismatches=int(np.count_nonzero(mask!=reference))
        assert header[1]==0 and list(map(int,header[10:16]))==[x,y,w,h,roi['source_width'],roi['source_height']]
        assert error==0 and mismatches==0
        return dict(id=row['id'],parent_id=row['parent_id'],variant=row['variant'],label=row['label'],
            score_error=error,mask_mismatches=mismatches,score_sha256=hashlib.sha256(scores.tobytes()).hexdigest(),mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
            frame_sequence=int(header[9]),alarm=int(header[2]),original_pixels_unchanged=True,
            engine_seconds=e['pl_engine_seconds'] if e else None)
    if a.mode=='c':
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,plan['images']))
    else:results=[run(row) for row in plan['images']]
    for parent in {r['parent_id'] for r in results}:
        group=[r for r in results if r['parent_id']==parent]
        assert len({r['score_sha256'] for r in group})==1 and len({r['mask_sha256'] for r in group})==1
    if a.mode=='board':assert all(b['frame_sequence']==a0['frame_sequence']+1 for a0,b in zip(results,results[1:]))
    summary=dict(scope='UNCHANGED_REAL_PHOTO_IN_SYNTHETIC_SURROUND_ENGINEERING_NOT_NEW_ACCURACY',mode=a.mode,cases=len(results),
        all_scores_masks_exact=True,outside_roi_mask_zero=True,background_invariant=True,original_pixels_unchanged=True,
        model_sha256=graph['sha256'],board_verified=a.mode=='board',new_material_accepted=False)
    save('results.json',results);save('summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
