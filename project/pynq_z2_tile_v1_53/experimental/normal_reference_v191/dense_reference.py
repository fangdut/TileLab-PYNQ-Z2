"""Offline normal-only reference coverage experiment; no runtime CPU inference."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/fpga_texture_v170'))
from prepare_integer import project,integer_scores
from export_integer import export

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 p=argparse.ArgumentParser()
 for n in ['base','dataset','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);start=time.monotonic()
 rows=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))['images']
 memory=[r for r in rows if r['role']=='memory'];cal=[r for r in rows if r['role']=='calibration'];tests=[r for r in rows if r['role']=='test']
 assert all(r['label']=='good' for r in memory+cal)
 assert not ({r['id'] for r in memory}&{r['id'] for r in cal+tests})
 assert not ({r['id'] for r in cal}&{r['id'] for r in tests})
 protocol=json.loads((a.base/'protocol.json').read_text())
 assert protocol['manifest_sha256']==sha(a.dataset/'manifest.json')
 assert set(protocol['memory_ids'])=={r['id'] for r in memory}
 assert set(protocol['threshold_ids'])=={r['id'] for r in cal}
 g=torch.load(a.base/'quantized_graph.pt',weights_only=True,map_location='cpu')
 assert g['side']==192
 h={k:v.copy() for k,v in np.load(a.base/'integer_head.npz',allow_pickle=False).items()}
 pw=torch.from_numpy(h['projection'].astype('i4'));bias=torch.from_numpy(h['bias'].astype('i8'));shift=int(h['shift']);grid=g['side']//8
 plan=dict(scope='OFFLINE_DENSE_NORMAL_REFERENCE_NOT_BOARD',side=192,centers=1024,
  pool='All existing integer feature positions of180 memory normals; no calibration/test images in center fit',
  threshold_rule='max of50 independent normal calibration image scores +1, fixed before test scoring',
  cnn_weights_trained=False,normal_reference_centers_refit=True,cnn_and_projection_unchanged=True,test_labels_used_for_fit=False,benchmark_is_blind=False,
  base_graph_sha256=sha(a.base/'quantized_graph.pt'),base_head_sha256=sha(a.base/'integer_head.npz'),manifest_sha256=sha(a.dataset/'manifest.json'),source_sha256=sha(Path(__file__)))
 save(a.out/'plan.json',plan);cache_hashes={};vectors=[];clipped=0
 def codes(r):
  f=a.base/'codes'/(r['id']+'.npy');v=np.load(f,allow_pickle=False)
  assert v.shape==(grid*grid,128) and v.dtype==np.int8
  cache_hashes[r['id']]=sha(f);return torch.from_numpy(v.astype('i4'))
 for r in memory:
  q=project(codes(r),pw,bias,shift);clipped+=int((q.abs()==32767).sum());vectors.append(q)
 pool=torch.cat(vectors);values=pool.double();norms=(values*values).sum(1);nearest=torch.full((len(pool),),float('inf'),dtype=torch.float64)
 selected=[];index=0
 # Integer coordinates: products and64-term sums stay below2^53, so float64 is exact.
 for i in range(1024):
  selected.append(index);distance=(norms+norms[index]-2*(values@values[index])).clamp_min(0)
  nearest=torch.minimum(nearest,distance);index=int(nearest.argmax())
  if (i+1)%128==0:print(f'Normal-only centers {i+1}/1024 pool={len(pool)} elapsed={time.monotonic()-start:.1f}s',flush=True)
 centers=pool[selected].contiguous();normal=[]
 for r in cal:
  scores=integer_scores(project(codes(r),pw,bias,shift),centers,grid)
  normal.append(dict(id=r['id'],score=int(scores.max())))
 threshold=max(r['score'] for r in normal)+1
 h['centers']=centers.numpy().astype('<i2');h['threshold']=np.array(threshold)
 np.savez_compressed(a.out/'integer_head.npz',**h);shutil.copyfile(a.base/'quantized_graph.pt',a.out/'quantized_graph.pt')
 meta=export(a.out,g,h,g['side']);model_hash=sha(a.out/'model.bin')
 save(a.out/'normal_calibration.json',normal);save(a.out/'selected_memory_indices.json',selected)
 # Freeze deployment bytes before reading test labels for reporting.
 save(a.out/'fit_complete.json',dict(model_sha256=model_hash,threshold=threshold,pool_positions=len(pool),memory_clipped_values=clipped,test_scoring_started=False))
 results=[]
 for r in tests:
  q=project(codes(r),pw,bias,shift);scores=integer_scores(q,centers,grid).numpy();score=int(scores.max())
  np.save(a.out/(r['id']+'_scores.npy'),scores,allow_pickle=False)
  results.append(dict(id=r['id'],label=r['label'],score=score,alarm=score>threshold,expected=r['label']!='good',projection_clipped_values=int((q.abs()==32767).sum())))
 assert sha(a.out/'model.bin')==model_hash
 tp=sum(r['alarm'] and r['expected'] for r in results);fp=sum(r['alarm'] and not r['expected'] for r in results)
 summary=dict(scope='OFFLINE_DENSE_NORMAL_REFERENCE_NOT_BOARD',cases=len(results),tp=tp,fp=fp,fn=sum(r['expected'] for r in results)-tp,tn=sum(not r['expected'] for r in results)-fp,
  cracks_detected=sum(r['alarm'] for r in results if r['label']=='crack'),threshold=threshold,side=192,centers=1024,model_sha256=model_hash,
  benchmark_is_blind=False,board_verified=False,rtl_verified=False,cnn_macs_per_frame=154183680,elapsed_seconds=time.monotonic()-start)
 save(a.out/'results.json',results);save(a.out/'cache_hashes.json',cache_hashes);save(a.out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
