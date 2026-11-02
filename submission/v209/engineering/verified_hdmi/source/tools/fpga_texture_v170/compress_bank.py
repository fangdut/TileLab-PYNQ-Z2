"""Offline normal-only greedy-codebook prefix compression, no CNN refitting."""
from pathlib import Path
import argparse,json,shutil
import numpy as np
import torch
from prepare_integer import project,integer_scores
from export_integer import export
from evaluate_lightweight import save,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--centers',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(8)
    original=np.load(a.base/'integer_head.npz',allow_pickle=False);head={k:original[k] for k in original.files}
    if not 1<=a.centers<len(head['centers']):raise ValueError('Choose a smaller nested codebook')
    head['centers']=head['centers'][:a.centers].copy();rows=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))['images']
    graph=torch.load(a.base/'quantized_graph.pt',weights_only=False,map_location='cpu');grid=graph['side']//8
    pw=torch.from_numpy(head['projection'].astype('i4'));bias=torch.from_numpy(head['bias']);centers=torch.from_numpy(head['centers'].astype('i4'))
    def scores(r):
        codes=torch.from_numpy(np.load(a.base/'codes'/(r['id']+'.npy')).astype('i4'))
        return integer_scores(project(codes,pw,bias,int(head['shift'])),centers,grid)
    normal=[dict(id=r['id'],score=int(scores(r).max())) for r in rows if r['role']=='calibration']
    head['threshold']=np.array(int(np.floor(np.quantile([r['score'] for r in normal],.95)))+1)
    np.savez_compressed(a.out/'integer_head.npz',**head);save(a.out/'normal_calibration.json',normal)
    protocol=json.loads((a.base/'protocol.json').read_text(encoding='utf8'));protocol.update(centers=a.centers,
        compression_source_head_sha256=sha(a.base/'integer_head.npz'),selection='Prefix of normal-only greedy covering sequence; threshold recalibrated on the same 50 normal calibration images',
        compression_source_code_sha256=sha(Path(__file__)))
    save(a.out/'protocol.json',protocol);results=[]
    for r in rows:
        if r['role']!='test':continue
        s=scores(r);peak=int(s.max());np.save(a.out/(r['id']+'_scores.npy'),s.numpy(),allow_pickle=False)
        results.append(dict(id=r['id'],label=r['label'],score=peak,alarm=peak>int(head['threshold']),expected=r['label']!='good'))
    tp=sum(r['alarm'] and r['expected'] for r in results);fp=sum(r['alarm'] and not r['expected'] for r in results)
    summary=dict(tp=tp,fp=fp,fn=84-tp,tn=33-fp,accuracy=(tp+33-fp)/117,recall=tp/84,
        cracks_detected=sum(r['alarm'] for r in results if r['label']=='crack'),threshold=int(head['threshold']),
        centers=a.centers,nn_operations_relative_to_base=a.centers/len(original['centers']),board_verified=False,all_integer_reference=True)
    save(a.out/'results.json',results);save(a.out/'summary.json',summary)
    metadata=export(a.out,graph,head,graph['side']);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
