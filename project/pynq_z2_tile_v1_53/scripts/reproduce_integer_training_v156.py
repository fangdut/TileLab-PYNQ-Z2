"""Rebuild the selected integer coefficients from recorded samples and real strips."""
from pathlib import Path
import sys,json,argparse,hashlib,time
import numpy as np
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'models'),str(R/'tools/v156')]
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from integer_boost_native import NativeBoost
from source_features import industrial_strip,RegionScorer
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--library',type=Path,default=R/'tools/v156/integer_boost_native.dll');args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False);threadpool_limits(2)
D=R/'reports/v156/training_reproduction';manifest=json.loads((D/'old_manifest.json').read_text());items=[r for r in manifest['rows'] if r['dataset']!='visuceram']
with np.load(D/'old_samples.npz') as d:x,y,g=d['x'],d['y'],d['group']
keep=np.isin(g,[r['index'] for r in items]);x,y=x[keep],y[keep];weights=np.load(D/'old_importance_weights.npy')[keep].copy();weights[y>0]*=8
teacher=RegionScorer(NativeBoost(json.loads((D/'mining_teacher.json').read_text()),args.library));fresh=[r for r in json.loads((R/'data/fresh_hfenet/manifest.json').read_text())['selected'] if r['split']=='development'];expected=json.loads((D/'mining_counts.json').read_text());rng=np.random.default_rng(156700);xx=[];ww=[];start=time.time()
for i,item in enumerate(fresh):
    image=R/item['image'];assert hashlib.sha256(image.read_bytes()).hexdigest()==item['image_sha256'];a=industrial_strip(image);score=teacher.predict(a['features'],a['inside']);inside=a['inside'];flat=a['features'].reshape(-1,12)
    counts=[]
    for pool,limit in zip([(score>=0)&inside,(score>=-262144)&(score<0)&inside,(score< -262144)&inside],[1024,512,256]):
        ids=np.flatnonzero(pool);chosen=rng.choice(ids,min(limit,len(ids)),replace=False) if len(ids) else ids
        if len(chosen):xx.append(flat[chosen]);ww.append(np.full(len(chosen),len(ids)/len(chosen),np.float64))
        counts.append(dict(population=len(ids),sampled=len(chosen)))
    assert counts==expected[i]['strata'],('Mining/preprocessing differs',i,counts,expected[i])
    if i%32==0:print(json.dumps(dict(mined_images=i+1,seconds=round(time.time()-start,1))),flush=True)
newx=np.concatenate(xx);trainx=np.concatenate([x,newx]);trainy=np.concatenate([y,np.zeros(len(newx),np.uint8)]);trainw=np.concatenate([weights,np.concatenate(ww)]);trainw/=trainw.mean()
model=HistGradientBoostingClassifier(max_iter=256,max_leaf_nodes=8,max_depth=3,min_samples_leaf=128,learning_rate=.15,l2_regularization=1,early_stopping=False,max_bins=255,random_state=156)
model.fit(trainx,trainy,sample_weight=trainw);trees=[]
for predictor in model._predictors:
    tree=[]
    for node in predictor[0].nodes:
        tree.append(dict(leaf=bool(node['is_leaf']),feature=int(node['feature_idx']),threshold=int(np.floor(node['num_threshold'])),left=int(node['left']),right=int(node['right']),value=int(np.rint(node['value']*65536))))
    trees.append(tree)
baseline=int(np.rint(model._baseline_prediction.ravel()[0]*65536));frozen=json.loads((R/'models/v156_integer_model.json').read_text());exact=baseline==frozen['baseline'] and trees==frozen['trees']
result=dict(exact_integer_coefficients=exact,baseline=baseline,trees=trees,training_samples=len(trainy),seconds=time.time()-start,scope='Retraining reproduction; never changes the frozen model or holdout outcomes.')
(args.out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='trees'}),flush=True)
if not exact:raise SystemExit('Library/thread arithmetic differs from the frozen coefficients; use the supplied frozen model for exact hardware verification.')
