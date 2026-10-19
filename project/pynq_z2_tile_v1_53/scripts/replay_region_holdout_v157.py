"""First reserved NORMAL evaluation after V157 regional policy freeze."""
from pathlib import Path
import sys,json,hashlib,datetime,time,argparse,concurrent.futures
import numpy as np
sys.dont_write_bytecode=True
ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--reproduction',action='store_true');ap.set_defaults(reproduction=True);args=ap.parse_args();R=args.project.resolve();O=args.out.resolve()
sys.path[:0]=[str(R/'models'),str(R/'tools/v156')]
from integer_boost_native import NativeBoost
from source_features import industrial_strip,RegionScorer
from integer_profile_v156 import mask_from_scores
from region_quality_reference_v157 import quality_regions
from scipy.ndimage import convolve
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();profile=json.loads((R/'models/v157_frozen_profile.json').read_text());assert profile['selection_frozen'];assert profile['min_trusted']==16 and profile['evidence_shift']==2
for rel,digest in profile['source_sha256'].items():assert sha(R/rel)==digest,rel
data=json.loads((R/'data/fresh_normal/manifest.json').read_text());items=[r for r in data['selected'] if r['split']=='reserved'];assert len(items)==512
assert len({r['group'] for r in items})==512 and len({r['effective_crop_sha256'] for r in items})==512
native=NativeBoost(json.loads((R/'models/v156_integer_model.json').read_text()),R/'tools/v156/integer_boost_native.dll');scorer=RegionScorer(native)
O.mkdir(parents=True,exist_ok=False);start=time.time();declaration=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope=('Reproduction of already disclosed fixed512 cohort; not a new blind test.' if args.reproduction else 'First and only new512 NORMAL holdout evaluation for frozen V157 policy; no crack recall, physical product independence, board or factory claim.'),images=512,profile_sha256=sha(R/'models/v157_frozen_profile.json'),model_id=profile['model_id'],algorithm_frozen_at=profile['created_at_utc'],data_frozen_at=data['created_at_utc'],physical_product_independence=False,script_sha256=sha(Path(__file__)))
(O/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n')
def run(item):
    path=R/item['image'];assert sha(path)==item['image_sha256'];f=industrial_strip(path);score=scorer.predict(f['features'],f['inside']);mask=mask_from_scores(f['n'],f['w'],f['s'],f['l'],score,f['inside']);raw=(score>=65536)&f['inside'];trusted=raw&(convolve(raw.astype(np.uint8),np.ones((3,3),np.uint8),mode='constant')>=5)
    full=np.zeros((720,1280),bool);evidence=np.zeros_like(full);full[64:656,64:1216]=mask;evidence[64:656,64:1216]=trusted;rows=[]
    for name,enabled in [('v156',False),('v157_region_evidence',True)]:
        q=quality_regions(full,evidence,enabled=enabled);rows.append(dict(id=item['image_sha256'][:16],group=item['group'],image=item['image'],image_sha256=item['image_sha256'],normal_by_source=True,variant=name,alarm=bool(q['boxes'] or q['overflow']),candidate_pixels=int(mask.sum()),raw_mask_sha256=hashlib.sha256(np.packbits(full.ravel(),bitorder='little').tobytes()).hexdigest(),**q))
    return rows
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for i,result in enumerate(pool.map(run,items)):
        rows.extend(result)
        if i%64==0:print(json.dumps(dict(images=i+1,seconds=round(time.time()-start,1))),flush=True)
summary=[]
for name in ['v156','v157_region_evidence']:
    rr=[r for r in rows if r['variant']==name];summary.append(dict(variant=name,images=len(rr),false_alarms=sum(r['alarm'] for r in rr),false_alarm_rate=sum(r['alarm'] for r in rr)/len(rr),raw_candidate_pixels=sum(r['candidate_pixels'] for r in rr)))
for rel,digest in profile['source_sha256'].items():assert sha(R/rel)==digest
result=dict(**declaration,summary=summary,rows=rows,seconds=time.time()-start,new_board_acceptance=False)
(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
