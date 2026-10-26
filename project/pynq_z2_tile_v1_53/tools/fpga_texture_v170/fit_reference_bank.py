"""OFFLINE normal-only reference calibration; never imported by deployment.

Keeps the accepted CNN, activation scales, projection and input arithmetic.
Only the 1024 normal centers and good-only threshold may change in model.bin.
File-disjoint public roof photographs do not establish independent specimens
or qualify a floor-tile inspection product.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, time
import numpy as np
import torch
from prepare_integer import FixedGraph, project, integer_scores
from export_integer import export

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a=parser.parse_args(); a.out.mkdir(exist_ok=False); (a.out/'codes').mkdir()
    started=time.monotonic(); torch.set_num_threads(8)
    manifest=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))
    plan=json.loads((a.dataset/'plan.json').read_text(encoding='utf8'))
    assert manifest['plan_sha256']==sha(a.dataset/'plan.json')
    rows=manifest['images']; memory=[r for r in rows if r['role']=='memory']
    cal=[r for r in rows if r['role']=='calibration']; tests=[r for r in rows if r['role']=='test']
    assert (len(memory),len(cal),len(tests))==(plan['memory_normals'],plan['calibration_normals'],40)
    assert all(r['label']=='good' for r in memory+cal)
    assert len({r['original_sha256'] for r in rows})==len(rows)
    for r in rows:
        assert sha(a.dataset/r['file'])==r['prepared_sha256']
    checkpoint=torch.load(a.base/'quantized_graph.pt',map_location='cpu',weights_only=False)
    head=dict(np.load(a.base/'integer_head.npz',allow_pickle=False))
    graph=FixedGraph.__new__(FixedGraph)
    for k,v in checkpoint.items(): setattr(graph,k,v)
    graph.feature_dim=128; graph.fixed_input=True
    graph.input_m=head['input_m']; graph.input_b=head['input_b']
    pw=torch.from_numpy(head['projection'].astype('i4'))
    bias=torch.from_numpy(head['bias'].astype('i8')); shift=int(head['shift'])
    def features(row):
        c=graph.forward(a.dataset/row['file'],integer=True,output_codes=True)
        np.save(a.out/'codes'/(row['id']+'.npy'), c.numpy().astype('i1'),allow_pickle=False)
        return project(c,pw,bias,shift)
    projected=[]
    for i,r in enumerate(memory):
        projected.append(features(r)); print(f'Normal reference {i+1}/{len(memory)}',flush=True)
    bank=torch.cat(projected).double(); nearest=torch.full((len(bank),),float('inf'),dtype=torch.float64)
    selected=[]; index=0
    for i in range(1024):
        selected.append(index)
        nearest=torch.minimum(nearest,((bank-bank[index])**2).sum(1)); index=int(nearest.argmax())
    centers=bank[selected].to(torch.int32); calibration=[]
    for r in cal:
        s=integer_scores(features(r),centers,28)
        calibration.append(dict(id=r['id'],score=int(s.max())))
    threshold=max(r['score'] for r in calibration)+1
    save(a.out/'normal_calibration.json',calibration)
    save(a.out/'center_selection.json',dict(indices=selected,normal_patch_count=len(bank)))
    head['centers']=centers.numpy().astype('<i2'); head['threshold']=np.array(threshold)
    np.savez_compressed(a.out/'integer_head.npz',**head)
    shutil.copy2(a.base/'quantized_graph.pt',a.out/'quantized_graph.pt')
    metadata=export(a.out,checkpoint,head,224)
    old=(a.base/'model.bin').read_bytes(); new=(a.out/'model.bin').read_bytes()
    header=np.frombuffer(old,dtype='<u4'); start=int(header[13])*8; stop=start+1024*64*2
    assert len(old)==len(new) and old[:60]==new[:60] and old[64:start]==new[64:start] and old[stop:]==new[stop:]
    assert sha(a.base/'quantized_graph.pt')==sha(a.out/'quantized_graph.pt')
    save(a.out/'calibration_frozen.json',dict(plan_sha256=sha(a.dataset/'plan.json'),
         manifest_sha256=sha(a.dataset/'manifest.json'),base_model_sha256=sha(a.base/'model.bin'),
         candidate_model_sha256=metadata['sha256'],threshold=threshold,
         only_binary_mutations=['header threshold bytes60:64',f'normal centers bytes{start}:{stop}'],
         unchanged_cnn_and_projection=True,test_scoring_started=False,
         license_note='Inherited fixed projection from MVTec development calibration retains baseline noncommercial limitations; new normal photos CC BY4.0',
         scope=plan['scope'],physical_specimen_independence=False))
    # Test is opened only after the candidate and threshold have been frozen.
    results=[]; base_centers=torch.from_numpy(np.load(a.base/'integer_head.npz')['centers'].astype('i4'))
    base_threshold=int(np.load(a.base/'integer_head.npz')['threshold'])
    for i,r in enumerate(tests):
        q=features(r); s=integer_scores(q,centers,28); b=integer_scores(q,base_centers,28)
        np.save(a.out/(r['id']+'_scores.npy'),s.numpy(),allow_pickle=False)
        results.append(dict(id=r['id'],label=r['label'],score=int(s.max()),alarm=bool(int(s.max())>threshold),
            baseline_score=int(b.max()),baseline_alarm=bool(int(b.max())>base_threshold),
            projection_clipped_values=int((q.abs()==32767).sum())))
        print(f'Frozen evaluation {i+1}/40',flush=True)
    def metrics(key):
        tp=sum(r[key] and r['label']!='good' for r in results); fp=sum(r[key] and r['label']=='good' for r in results)
        return dict(tp=tp,fp=fp,tn=20-fp,fn=20-tp,accuracy=(tp+20-fp)/40,normal_false_positive_rate=fp/20,defect_recall=tp/20)
    summary=dict(candidate=metrics('alarm'),baseline=metrics('baseline_alarm'),threshold=threshold,
        model_sha256=metadata['sha256'],elapsed_seconds=time.monotonic()-started,
        board_verified=False,accuracy_acceptance=False,scope=plan['scope'],
        note='Exploratory file-disjoint roof ceramic pilot; no floor-tile or independent-specimen claim')
    save(a.out/'results.json',results); save(a.out/'summary.json',summary)
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
