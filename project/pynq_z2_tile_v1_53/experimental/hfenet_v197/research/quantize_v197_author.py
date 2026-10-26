"""Post-training integer feasibility audit. No training, GPU or station changes."""
from pathlib import Path
import sys,json,hashlib,contextlib,io,zipfile,time,datetime
import numpy as np,torch
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');S=W/'v197_hfenet_source01';O=W/'v197_integer01';O.mkdir(exist_ok=False)
sys.path[:0]=[str(S),str(W/'v197_hfe_runtime'),str(P/'experimental/hfenet_v197')]
import cv2
from hfenet import HFENet
from integer_reference import Calibrator,IntegerGraph
torch.set_num_threads(8);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=dict(scope='OFFLINE_INTEGER_MIGRATION_AUTHOR_DATA_NOT_BOARD_OR_INDEPENDENT_ACCEPTANCE',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkpoint_sha256=sha(S/'checkpoint/model_epoch_69.pth'),integer_source_sha256=sha(P/'experimental/hfenet_v197/integer_reference.py'),calibration_manifest_sha256=sha(W/'v196_dataset_hfe01/manifest.json'),test_manifest_sha256=sha(W/'v197_new80_01/manifest.json'),training=False,device='CPU_OFFLINE_ONLY',activation_bits=16,weight_bits=16,normalization='Integer moments; arbitrary-precision variance, integer sqrt, Q30 gamma/beta, dynamic Q36 affine, nearest-even; full graph integer geometry',mac_oracle='Float64 exact INTEGER operands, all partial sums bounded<2**53; future RTL must verify integer hardware',new_geometry='original256x1408; does not fit existing1024perdim station contract',margin=2,pixel_decision='integer final logit>0, no sigmoid hardware',author_validation_data=True)
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
net.load_state_dict(torch.load(S/'checkpoint/model_epoch_69.pth',map_location='cpu',weights_only=True)['model']);net.eval();graph=torch.fx.symbolic_trace(net)
z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip')
def input_image(row):
    raw=z.read(row['archive_path']);assert hashlib.sha256(raw).hexdigest()==row['original_sha256'];image=np.asarray(Image.open(io.BytesIO(raw)).convert('L'));eq=cv2.equalizeHist(image);merged=np.stack([image,eq,cv2.add(image,eq)],axis=0).copy()
    return torch.from_numpy(merged).float()[None]
rows=json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images'];cal=Calibrator(graph)
for i,row in enumerate(r for r in rows if r['role']=='calibration'):
    with torch.inference_mode():cal.run(input_image(row))
    if i%8==7:
        (O/'progress.json').write_text(json.dumps(dict(stage='calibration',completed=i+1,total=64)),encoding='utf8');print('CALIBRATION',i+1,flush=True)
calibration=cal.export();(O/'calibration_frozen.json').write_text(json.dumps(calibration,indent=2),encoding='utf8');reference=IntegerGraph(graph,calibration)
weights={};weight_exponents={}
for name,(q,exp) in reference.weights.items():weights[name]=q.numpy().astype('i2');weight_exponents[name]=exp
np.savez_compressed(O/'integer_weights.npz',**weights)
(O/'weight_exponents.json').write_text(json.dumps(weight_exponents,indent=2),encoding='utf8')
(O/'export_frozen.json').write_text(json.dumps(dict(weights_sha256=sha(O/'integer_weights.npz'),calibration_sha256=sha(O/'calibration_frozen.json'),test_scoring_started=False,training=False),indent=2),encoding='utf8')
test=json.loads((W/'v197_new80_01/manifest.json').read_text())['images'];float_results=[r for r in json.loads((W/'v197_author01/results.json').read_text()) if r['view']=='original'];byid={r['id']:r for r in float_results};results=[];(O/'masks').mkdir();max_variance_bits=0;max_affine_bits=0
for i,row in enumerate(test):
    started=time.perf_counter();reference.clipped={};reference.norm_records=[];reference.trace=[]
    with torch.inference_mode():out=reference.run(input_image(row))
    pred=out.q.numpy()[0,0].astype(bool);label_path=row['archive_path'].replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';gt=np.asarray(Image.open(io.BytesIO(z.read(label_path))).convert('L'))>1
    original=np.asarray(Image.open(W/'v197_author01/masks'/(row['id']+'_original.png')).convert('L'))>1
    Image.fromarray((pred*255).astype('u1')).save(O/'masks'/(row['id']+'.png'))
    result=dict(id=row['id'],label='defect' if gt.any() else 'good',alarm=bool(pred.any()),positive_pixels=int(pred.sum()),float_alarm=byid[row['id']]['raw_alarm'],float_mask_disagreement=int((pred!=original).sum()),pixel_tp=int((pred&gt).sum()),pixel_fp=int((pred&~gt).sum()),pixel_fn=int((~pred&gt).sum()),clipped_values=sum(reference.clipped.values()),clipped_by_node=reference.clipped,offline_cpu_seconds=time.perf_counter()-started)
    results.append(result)
    for layer in reference.norm_records:
        for c in layer['channels']:
            max_variance_bits=max(max_variance_bits,c['variance'].bit_length());max_affine_bits=max(max_affine_bits,abs(c['a']).bit_length(),abs(c['b']).bit_length())
    if i==0:
        (O/'first_norm_records_local.json').write_text(json.dumps(reference.norm_records,indent=2),encoding='utf8');(O/'integer_trace.json').write_text(json.dumps(reference.trace,indent=2),encoding='utf8')
    (O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');(O/'progress.json').write_text(json.dumps(dict(stage='integer_test',completed=i+1,total=80)),encoding='utf8')
    print('INTEGER',i+1,'alarm',result['alarm'],'clip',result['clipped_values'],'seconds',result['offline_cpu_seconds'],flush=True)
tp=sum(r['label']=='defect' and r['alarm'] for r in results);fp=sum(r['label']=='good' and r['alarm'] for r in results);pt=sum(r['pixel_tp'] for r in results);pf=sum(r['pixel_fp'] for r in results);pn=sum(r['pixel_fn'] for r in results)
summary=dict(scope=plan['scope'],cases=80,tp=tp,fp=fp,tn=40-fp,fn=40-tp,float_image_decisions_unchanged=all(r['alarm']==r['float_alarm'] for r in results),float_mask_disagreement=sum(r['float_mask_disagreement'] for r in results),total_pixels=80*256*1408,pixel_iou=pt/(pt+pf+pn),total_clipped_values=sum(r['clipped_values'] for r in results),max_variance_bits=max_variance_bits,max_affine_coefficient_bits=max_affine_bits,board_verified=False,rtl_full_graph_verified=False,training=False)
(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
