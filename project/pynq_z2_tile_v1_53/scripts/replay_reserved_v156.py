"""One-shot reserved-normal evaluation after the algorithm/model freeze."""
from pathlib import Path
import sys,json,hashlib,time,datetime,concurrent.futures
import numpy as np
from PIL import Image
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parents[1];W=R/'tools/v156';sys.path[:0]=[str(W),str(R/'models')]
from integer_boost_native import NativeBoost
from integer_profile_v156 import mask_from_scores
from tree_features_v155 import feature_matrix
from valley_reference import valley
from directional_link_reference import direction_planes,shoulder_noise,masks,propagate
from regions_reference import regions
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
F=R/'models/v156_frozen_profile.json';profile=json.loads(F.read_text());assert profile['selection_frozen'] is True
for p,digest in profile['source_sha256'].items():assert sha(R/p)==digest,('Frozen source changed',p)
proof=json.loads((R/'reports/v156/native_reference_proof.json').read_text());assert proof['exact'] and proof['model_sha256']==sha(R/'models/v156_integer_model.json') and proof['dll_sha256']==sha(W/'integer_boost_native.dll')
model=json.loads((R/'models/v156_integer_model.json').read_text());native=NativeBoost(model,W/'integer_boost_native.dll');table=np.zeros((256,12),np.uint8);table[:,6]=np.arange(256);table[:,7]=np.arange(256);table[:,10]=255;background_scores=native.predict(table)
data=json.loads((R/'data/fresh_hfenet/manifest.json').read_text());items=[r for r in data['selected'] if r['split']=='reserved'];assert len(items)==192
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();O=args.out;O.mkdir(parents=True,exist_ok=False)
decl=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Reproduction of the already-reported fixed reserved cohort; not a new blind test. Source-labeled NORMAL industrial strips only; not crack-recall, physical-board or factory validation. Do not retune this candidate using outcomes.',profile_sha256=sha(F),algorithm_frozen_at=profile['created_at_utc'],data_split_frozen_at=data['created_at_utc'],images=len(items),physical_product_independence=False,native_proof=proof,script_sha256=sha(Path(__file__)))
(O/'declaration.json').write_text(json.dumps(decl,indent=2));start=time.time()
def evaluate(item):
 p=R/item['image'];lab=R/item['label'];assert sha(p)==item['image_sha256'] and sha(lab)==item['label_sha256']
 with Image.open(lab) as im:assert not np.asarray(im).any(),'Normal source label is not empty'
 with Image.open(p) as im:a=np.asarray(im.rotate(-90,expand=True).convert('RGB')).astype(np.int32)
 gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8;g=np.zeros((592,1152),np.int32);g[168:424,16:1136]=gray[:,144:1264]
 n=valley(g,8);w=valley(g,16);s=direction_planes(g,8);l=direction_planes(g,16);s4=direction_planes(g,8,4);l8=direction_planes(g,16,8);noise=shoulder_noise(g)
 features=feature_matrix(g,n,w,s,l,s4,l8,noise);inside=np.zeros(g.shape,bool);inside[16:576,16:1136]=True
 ids=np.flatnonzero(inside.ravel());x=features.reshape(-1,12)[ids];constant=(~np.any(x[:,:6],axis=1))&(x[:,6]==x[:,7])&(x[:,8]==0)&(x[:,9]==0)&(x[:,10]==255)&(x[:,11]==0)
 values=np.empty(len(ids),np.int32);values[constant]=background_scores[x[constant,6]];values[~constant]=native.predict(x[~constant]);score=np.full(g.shape,-1073741824,np.int32);score.ravel()[ids]=values
 seed,weak,dirs=masks(n,w,s,l);seed&=inside;weak&=inside;dirs&=inside;line=s4.max(axis=0)
 masks_by_name=dict(v154=propagate(seed,weak,dirs),conservative=propagate(seed|((line>60)&inside),weak|((line>30)&inside),dirs),sensitive=propagate(seed,weak,dirs,passes=8,mode='tangent'),v156_integer_boost=mask_from_scores(n,w,s,l,score,inside))
 rows=[]
 for name,mask in masks_by_name.items():
  full=np.zeros((720,1280),bool);full[64:656,64:1216]=mask;rr=regions(full)
  rows.append(dict(dataset='hfenet_fresh_reserved',id=item['image_sha256'][:16],source_group=item['group'],image=item['image'],image_sha256=item['image_sha256'],variant=name,normal_by_source=True,alarm=bool(rr['boxes'] or rr['overflow']),pixels=int(mask.sum()),boxes=rr['boxes'],areas=rr['areas'],overflow=rr['overflow'],mask_sha256=hashlib.sha256(np.packbits(full.ravel(),bitorder='little').tobytes()).hexdigest()))
 return rows
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for i,result in enumerate(pool.map(evaluate,items)):
  rows.extend(result)
  if i%32==0:print(json.dumps(dict(images=i+1,seconds=round(time.time()-start,1))),flush=True)
assert sha(F)==decl['profile_sha256']
for p,digest in profile['source_sha256'].items():assert sha(R/p)==digest
summary=[]
for name in ['v154','conservative','sensitive','v156_integer_boost']:
 group=[r for r in rows if r['variant']==name];summary.append(dict(variant=name,images=len(group),false_alarms=sum(r['alarm'] for r in group),false_alarm_rate=sum(r['alarm'] for r in group)/len(group),false_pixels=sum(r['pixels'] for r in group)))
(O/'summary.json').write_text(json.dumps(dict(**decl,summary=summary,rows=rows,seconds=time.time()-start,new_board_acceptance=False),indent=2));print(json.dumps(summary,indent=2),flush=True)
