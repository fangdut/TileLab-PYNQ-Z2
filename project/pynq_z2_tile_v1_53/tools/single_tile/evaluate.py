"""Re-run exposed50-image development OOF, not an independent accuracy test."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from PIL import Image
from detector import ROOT,infer,read_input,save_result,load
from fine_integer_native import NativeBoost

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--native-library',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--input-kind',required=True,choices=['stimulus','historical_acquired']);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);start=time.perf_counter();p=load(ROOT)
    oof=json.loads((ROOT/'models/oof_v159/manifest.json').read_text());folds={r['id']:r['fold'] for r in oof['rows']}
    models={};backends={}
    for i in range(3):
        name=f'fold{i}.json';path=ROOT/'models/oof_v159'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=oof['fold_model_sha256'][name]:raise ValueError('OOF model hash mismatch')
        models[i]=json.loads(path.read_text());backends[i]=NativeBoost(models[i],a.native_library)
    data=ROOT/'data/real_tiles';items=[r for r in json.loads((data/'hdmi_manifest.json').read_text())['items'] if r['id'] in folds];truth_index={r['id']:r for r in json.loads((data/'manifest.json').read_text())['samples']}
    if len(items)!=50 or any(r['label'] not in ('crack','good') for r in items):raise ValueError('Expected exactly17 crack and33 normal exposed images')
    rows=[]
    for item in items:
        image=data/item['image'] if a.input_kind=='stimulus' else ROOT/f"validation/reference_rgb/real_{item['index']:03}_original.png"
        rgb=read_input(image);fold=folds[item['id']];mask,result=infer(rgb,models[fold],backends[fold]);truth=np.zeros(mask.shape,bool)
        truth_path=truth_index[item['id']].get('mask')
        if truth_path:
            with Image.open(data/truth_path) as im:truth[110:610,390:890]=np.asarray(im.convert('L').resize((500,500),Image.Resampling.NEAREST))>0
        boxes=result['regions']['boxes'];associated=any((truth[y0:y1+1,x0:x1+1]&mask[y0:y1+1,x0:x1+1]).any() for x0,y0,x1,y1 in boxes)
        row=dict(index=item['index'],id=item['id'],label=item['label'],fold=fold,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),tp=int((mask&truth).sum()),fp=int((mask&~truth).sum()),truth=int(truth.sum()),localized_alarm=bool(result['alarm'] and associated),**result)
        rows.append(row);save_result(a.out/f"sample_{item['index']:03}",rgb,mask,row);print(json.dumps({k:row[k] for k in ('index','label','alarm','localized_alarm','tp','fp','truth')}),flush=True)
    positive=[r for r in rows if r['truth']];normal=[r for r in rows if r['label']=='good'];tp=sum(r['tp'] for r in rows);fp=sum(r['fp'] for r in rows);gt=sum(r['truth'] for r in rows)
    report=dict(scope='EXPOSED_DEVELOPMENT_OOF_NOT_INDEPENDENT_NOT_CURRENT_BOARD_TEST',input_kind=a.input_kind,qualified=False,requested_materials=['painted','multiple_materials'],requested_materials_qualified=False,profile_sha256=p['profile_sha256'],image_positive=len(positive),image_negative=len(normal),localized_crack_detections=sum(r['localized_alarm'] for r in positive),missed_crack_images=sum(not r['localized_alarm'] for r in positive),normal_false_alarms=sum(r['alarm'] for r in normal),normal_image_fpr=sum(r['alarm'] for r in normal)/len(normal),pixel_precision=tp/(tp+fp),pixel_recall=tp/gt,worst_crack_pixel_recall=min(r['tp']/r['truth'] for r in positive),gt_pixels=gt,roi_excluded_gt_pixels=0,seconds=time.perf_counter()-start,source_oof_scope=oof['scope'],rows=rows)
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
