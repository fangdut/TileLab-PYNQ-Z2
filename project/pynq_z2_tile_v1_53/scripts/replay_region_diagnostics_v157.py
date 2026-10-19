"""Reproduce regional decisions from recorded exposed-development pixel/evidence maps."""
from pathlib import Path
import argparse,sys,json,hashlib
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from region_quality_reference_v157 import quality_regions
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
profile=json.loads((R/'models/v157_frozen_profile.json').read_text())
for rel,digest in profile['source_sha256'].items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==digest
summary=[]
for cohort in ['old_development','fresh156_development','exposed192','new_development','positive_training']:
    D=R/'reports/v157/development'/cohort;data=json.loads((D/'summary.json').read_text());baseline=qualified=true_overlap=0
    for item in data['rows']:
        with np.load(D/(item['id']+'.npz')) as a:
            assert hashlib.sha256(np.packbits(a['mask'].ravel(),bitorder='little').tobytes()).hexdigest()==item['mask_sha256']
            full=np.zeros((720,1280),bool);trusted=np.zeros_like(full);full[64:656,64:1216]=a['mask'];trusted[64:656,64:1216]=a['trusted']
        old=quality_regions(full,trusted,False);new=quality_regions(full,trusted,True)
        expected=[c for c in item['components'] if c['trusted']>=16 and c['trusted']*4>=c['pixels']]
        assert new['boxes']==[c['box'] for c in expected[:8]] and new['areas']==[c['pixels'] for c in expected[:8]]
        assert new['trusted']==[c['trusted'] for c in expected[:8]] and new['overflow']==(len(expected)>8)
        assert bool(old['boxes'] or old['overflow'])==item['baseline_alarm']
        baseline+=bool(old['boxes'] or old['overflow']);qualified+=bool(new['boxes'] or new['overflow']);true_overlap+=any(c['tp'] for c in expected)
    summary.append(dict(cohort=cohort,images=len(data['rows']),baseline_alarms=baseline,qualified_alarms=qualified,true_overlap_alarms=true_overlap))
(args.out/'proof.json').write_text(json.dumps(dict(all_masks_and_regions_exact=True,summary=summary,scope='Reproduction of exposed diagnostics/training replay, not new validation.'),indent=2)+'\n');print(json.dumps(summary,indent=2))
