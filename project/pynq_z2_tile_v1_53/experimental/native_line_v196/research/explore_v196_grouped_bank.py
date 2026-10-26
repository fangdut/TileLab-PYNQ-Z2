"""Normal-only reference groups; both evaluation file sets are now exposed.

Tests whether pooled-material calibration, rather than CNN sensitivity alone,
causes the failure. Not a deployed host classifier or a blind accuracy claim.
"""
from pathlib import Path
import sys,json,numpy as np,torch
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');D=W/'v196_dataset_hfe01';O=W/'v196_grouped_reference01';O.mkdir(exist_ok=False)
sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
from prepare_integer import FixedGraph,project,integer_scores
torch.set_num_threads(8);head=dict(np.load(W/'v170_fullint224/integer_head.npz'));pw=torch.from_numpy(head['projection'].astype('i4'));bias=torch.from_numpy(head['bias'])
rows=json.loads((D/'manifest.json').read_text())['images'];q={};desc={}
def add(row,folder):
    c=torch.from_numpy(np.load(folder/(row['id']+'.npy')).astype('i4'));v=project(c,pw,bias,int(head['shift']));q[row['id']]=v
    total=v.to(torch.int64).sum(0);desc[row['id']]=torch.sign(total)*((total.abs()+392)//784)
for r in rows:add(r,W/'v196_hfe_reference01/codes')
memory=[r for r in rows if r['role']=='memory'];cal=[r for r in rows if r['role']=='calibration'];x=torch.stack([desc[r['id']] for r in memory]);nearest=torch.full((len(x),),float('inf'),dtype=torch.float64);indices=[];idx=0
for _ in range(10):
    indices.append(idx);nearest=torch.minimum(nearest,((x.double()-x[idx].double())**2).sum(1));idx=int(nearest.argmax())
rep=x[indices].clone()
for _ in range(30):
    dist=((x[:,None,:]-rep[None,:,:])**2).sum(2);assignment=dist.argmin(1);updated=rep.clone()
    for g in range(10):
        members=x[assignment==g]
        if len(members):
            total=members.sum(0);updated[g]=torch.sign(total)*((total.abs()+len(members)//2)//len(members))
    if torch.equal(rep,updated):break
    rep=updated
def group(row):return int(((rep-desc[row['id']])**2).sum(1).argmin())
banks={};groups={};thresholds={};protocol=[]
for g in range(10):
    mr=[r for r in memory if group(r)==g];cr=[r for r in cal if group(r)==g]
    groups[g]=dict(memory=len(mr),calibration=len(cr));print('GROUP',g,groups[g],flush=True)
    if not mr or not cr:continue
    bank=torch.cat([q[r['id']] for r in mr]).double();nearest=torch.full((len(bank),),float('inf'),dtype=torch.float64);selected=[];idx=0
    for _ in range(min(1024,len(bank))):
        selected.append(idx);nearest=torch.minimum(nearest,((bank-bank[idx])**2).sum(1));idx=int(nearest.argmax())
    centers=bank[selected].to(torch.int32);banks[g]=centers
    normal=[dict(id=r['id'],score=int(integer_scores(q[r['id']],centers,28).max())) for r in cr]
    thresholds[g]=max(r['score'] for r in normal)+1;protocol.append(dict(group=g,normal=normal,threshold=thresholds[g],centers=len(centers)))
np.savez_compressed(O/'groups.npz',representatives=rep.numpy().astype('i2'),**{f'bank_{g}':v.numpy().astype('i2') for g,v in banks.items()})
(O/'normal_calibration.json').write_text(json.dumps(dict(groups=groups,calibration=protocol,scope='NORMAL_ONLY_REFERENCE_GROUP_DESIGN_NOT_FLOWER_GROUND_TRUTH',test_scoring_started=False),indent=2),encoding='utf8')
tests=[dict(r,group_set='original40') for r in rows if r['role']=='test'];new=json.loads((W/'v196_hfe_holdout01/manifest.json').read_text())['images']
checkpoint=torch.load(W/'v170_fullint224/quantized_graph.pt',map_location='cpu',weights_only=False);graph=FixedGraph.__new__(FixedGraph)
for k,v in checkpoint.items():setattr(graph,k,v)
graph.feature_dim=128;graph.fixed_input=True;graph.input_m=head['input_m'];graph.input_b=head['input_b'];cache=O/'new_codes';cache.mkdir()
for r in new:
    c=graph.forward(W/'v196_hfe_holdout01'/r['file'],integer=True,output_codes=True);np.save(cache/(r['id']+'.npy'),c.numpy().astype('i1'));add(r,cache)
tests.extend(dict(r,group_set='opened40') for r in new);results=[];metrics={}
for r in tests:
    g=group(r);score=int(integer_scores(q[r['id']],banks[g],28).max()) if g in banks else None
    results.append(dict(id=r['id'],label=r['label'],group=g,group_set=r['group_set'],score=score,threshold=thresholds.get(g),alarm=bool(score>thresholds[g]) if score is not None else None))
for name in ['original40','opened40']:
    subset=[r for r in results if r['group_set']==name];tp=sum(r['alarm'] is True for r in subset if r['label']=='defect');fp=sum(r['alarm'] is True for r in subset if r['label']=='good')
    metrics[name]=dict(tp=tp,fp=fp,fn=20-tp,good_unknown=sum(r['alarm'] is None for r in subset if r['label']=='good'),defect_unknown=sum(r['alarm'] is None for r in subset if r['label']=='defect'))
(O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');(O/'summary.json').write_text(json.dumps(dict(scope='EXPOSED_DEVELOPMENT_REFERENCE_GROUP_ABLATION_NOT_BOARD',metrics=metrics,groups=groups,host_runtime_classification=False),indent=2),encoding='utf8');print(json.dumps(metrics))
