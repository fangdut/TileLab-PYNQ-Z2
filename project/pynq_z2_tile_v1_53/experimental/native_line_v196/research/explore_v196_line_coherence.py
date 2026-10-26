from pathlib import Path
from PIL import Image
import numpy as np,json
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');D=W/'v196_dataset_hfe01';O=W/'v196_line_coherence01';O.mkdir(exist_ok=False)
rows=json.loads((D/'manifest.json').read_text())['images'];spans=[2,4,8];methods=['energy_weighted','ratio_energy_floor','count_contrast2','gate_three_quarters']
def features(row):
    a=np.asarray(Image.open(D/row['file']).convert('RGB'),dtype=np.int64);height,width=a.shape[:2]
    yy=np.clip((2*np.arange(224)+1)*height-224,0,(height-1)*448)//448
    y=((a[:,:,0]+2*a[:,:,1]+a[:,:,2])//4)[yy];out={k:[] for k in methods}
    for d in spans:
        r=2*y[:,d:width-d]-y[:,:width-2*d]-y[:,2*d:];n=np.abs(r.sum(0));e=np.abs(r).sum(0)
        values=dict(energy_weighted=n*n//(e+1),ratio_energy_floor=np.where(e>=448,n*256//(e+1),0),
            count_contrast2=np.maximum((r>2).sum(0),(r<-2).sum(0)),gate_three_quarters=np.where(n*4>e*3,n,0))
        for key in methods:out[key].append(int(values[key].max()))
    return dict(id=row['id'],label=row['label'],values=out)
cal=[features(r) for r in rows if r['role']=='calibration'];thresholds={k:[max(r['values'][k][i] for r in cal)+1 for i in range(3)] for k in methods}
(O/'frozen_calibration.json').write_text(json.dumps(dict(thresholds=thresholds,spans=spans,calibration=cal,
    scope='Normal-only calibration; test set already exposed during CNN failure, development only'),indent=2),encoding='utf8')
results=[features(r) for r in rows if r['role']=='test'];summaries={}
for key in methods:
    alarm=[any(s>t for s,t in zip(r['values'][key],thresholds[key])) for r in results]
    tp=sum(v and r['label']=='defect' for r,v in zip(results,alarm));fp=sum(v and r['label']=='good' for r,v in zip(results,alarm))
    summaries[key]=dict(tp=tp,fp=fp,tn=20-fp,fn=20-tp)
(O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8');(O/'summary.json').write_text(json.dumps(dict(scope='OFFLINE_EXPOSED_DEVELOPMENT_NOT_BOARD',thresholds=thresholds,metrics=summaries),indent=2),encoding='utf8')
print(json.dumps(dict(thresholds=thresholds,metrics=summaries)))
