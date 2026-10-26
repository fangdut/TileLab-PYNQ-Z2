"""Published checkpoint reproduction only; never imported by station runtime."""
from pathlib import Path
import sys,json,hashlib,zipfile,io,time,contextlib,datetime
import numpy as np,torch
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');S=W/'v197_hfenet_source01';O=W/'v197_author01';O.mkdir(exist_ok=False)
sys.path.insert(0,str(W/'v197_hfe_runtime'));sys.path.insert(0,str(S));import cv2
from hfenet import HFENet
torch.set_num_threads(8);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((S/'source.json').read_text());plan=dict(scope='AUTHOR_CHECKPOINT_ON_AUTHOR_DATA_REPRODUCTION_NOT_INDEPENDENT_VALIDATION',source=source,probability_threshold=.5,primary_image_rule='any predicted pixel >0.5',secondary_rule='predicted positive pixel count > maximum64 good calibration positive pixel counts; separate thresholds for crop and original',views=['unchanged256x704_crop','unchanged256x1408_original'],training=False,gpu_used=False,runtime_station_modified=False,checkpoint_chosen_before_smoke=True,two_crop_smoke_inputs_already_observed=True,preprocess='Author: original grayscale, OpenCV equalizeHist, saturated uint8 add; channel stack; float32 0..255, no division by255; no resize',opencv_version=cv2.__version__,torch_version=torch.__version__,author_validation_data=True,author_checkpoint_selection_overlap_unknown=True,frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
net.load_state_dict(torch.load(S/'checkpoint/model_epoch_69.pth',map_location='cpu',weights_only=True)['model'],strict=True);net.eval()
z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');hooks=[];calls=[]
def hook(name):
    def h(module,inputs,output):
        if isinstance(module,torch.nn.Conv2d):calls.append(dict(name=name,input=list(inputs[0].shape),output=list(output.shape),kernel=list(module.kernel_size),dilation=list(module.dilation),groups=module.groups,macs=output.numel()*(module.in_channels//module.groups)*module.kernel_size[0]*module.kernel_size[1],parameters=sum(p.numel() for p in module.parameters())))
    return h
def forward(gray,profile=False):
    eq=cv2.equalizeHist(gray);image=np.stack([gray,eq,cv2.add(gray,eq)],axis=0).copy();started=time.perf_counter()
    if profile:
        for name,module in net.named_modules():
            if isinstance(module,torch.nn.Conv2d):hooks.append(module.register_forward_hook(hook(name)))
    with torch.inference_mode():out=net(torch.from_numpy(image).float()[None]).numpy()[0,0]
    if profile:
        for h in hooks:h.remove()
    return out,time.perf_counter()-started
def originals(row):
    raw=z.read(row['archive_path']);assert hashlib.sha256(raw).hexdigest()==row['original_sha256'];gray=np.asarray(Image.open(io.BytesIO(raw)).convert('L'))
    path=row['archive_path'].replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';mask=np.asarray(Image.open(io.BytesIO(z.read(path))).convert('L'))>1
    return gray,mask
norm=json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images'];cal=[r for r in norm if r['role']=='calibration'];calibration=[]
for i,row in enumerate(cal):
    gray,gt=originals(row);assert not gt.any();x,y,w,h=row['crop']
    for view,image in [('crop',gray[y:y+h,x:x+w]),('original',gray)]:
        out,seconds=forward(image,profile=i==0 and view=='original');calibration.append(dict(id=row['id'],view=view,positive_pixels=int((out>.5).sum()),peak=float(out.max()),offline_cpu_seconds=seconds))
    if i%8==7:
        (O/'progress.json').write_text(json.dumps(dict(stage='normal_calibration',completed=i+1,total=64)),encoding='utf8');print('NORMAL',i+1,flush=True)
thresholds={view:max(r['positive_pixels'] for r in calibration if r['view']==view) for view in ['crop','original']}
(O/'calibration_frozen.json').write_text(json.dumps(dict(calibration=calibration,thresholds=thresholds,test_scoring_started=False,checkpoint_sha256=sha(S/'checkpoint/model_epoch_69.pth')),indent=2),encoding='utf8')
(O/'executed_graph.json').write_text(json.dumps(dict(declared_parameters=sum(p.numel() for p in net.parameters()),executed_conv_layers=len(calls),executed_conv_parameters=sum(c['parameters'] for c in calls),macs_original=sum(c['macs'] for c in calls),calls=calls,dynamic_instance_norm='17 executed, per-input statistics; cannot fold as fixed BatchNorm',largest_single_float32_activation_bytes=max(np.prod(c['output'])*4 for c in calls).item()),indent=2),encoding='utf8')
rows=json.loads((W/'v197_new80_01/manifest.json').read_text())['images'];results=[];(O/'masks').mkdir()
for i,row in enumerate(rows):
    gray,gt=originals(row);x,y,w,h=row['crop']
    for view,image,truth in [('crop',gray[y:y+h,x:x+w],gt[y:y+h,x:x+w]),('original',gray,gt)]:
        out,seconds=forward(image);pred=out>.5;tp=int((pred&truth).sum());fp=int((pred&~truth).sum());fn=int((~pred&truth).sum())
        result=dict(id=row['id'],view=view,label='defect' if truth.any() else 'good',positive_pixels=int(pred.sum()),peak=float(out.max()),raw_alarm=bool(pred.any()),calibrated_area_alarm=bool(pred.sum()>thresholds[view]),pixel_tp=tp,pixel_fp=fp,pixel_fn=fn,offline_cpu_seconds=seconds)
        results.append(result);Image.fromarray((pred*255).astype('u1')).save(O/'masks'/(row['id']+'_'+view+'.png'))
    (O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    (O/'progress.json').write_text(json.dumps(dict(stage='test',completed=i+1,total=80)),encoding='utf8')
    if i%10==9:print('TEST',i+1,flush=True)
metrics={}
for view in ['crop','original']:
    rr=[r for r in results if r['view']==view];metrics[view]={}
    for decision in ['raw_alarm','calibrated_area_alarm']:
        tp=sum(r['label']=='defect' and r[decision] for r in rr);fp=sum(r['label']=='good' and r[decision] for r in rr);ng=sum(r['label']=='good' for r in rr);nd=len(rr)-ng
        metrics[view][decision]=dict(tp=tp,fp=fp,tn=ng-fp,fn=nd-tp,n_good=ng,n_defect=nd)
    pt=sum(r['pixel_tp'] for r in rr);pf=sum(r['pixel_fp'] for r in rr);pn=sum(r['pixel_fn'] for r in rr);metrics[view]['defect_pixel_iou']=pt/(pt+pf+pn) if pt+pf+pn else 1
summary=dict(scope=plan['scope'],metrics=metrics,normal_only_area_thresholds=thresholds,board_verified=False,training=False,hardware_migrated=False,station_modified=False,author_validation_overlap_not_excluded=True)
(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
