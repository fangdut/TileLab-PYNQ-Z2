"""Exact original-photo pixels inside two synthetic surrounds: engineering only.

These are not new real defect samples or a manufacturing acceptance dataset.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    rows=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))['images'];chosen=[]
    for label in ['good','crack']:
        subset=sorted((r for r in rows if r['role']=='test' and r['label']==label),key=lambda r:hashlib.sha256(('v196-background-engineering|'+r['id']).encode()).hexdigest())
        chosen.extend(subset[:2])
    yy,xx=np.indices((1000,1000));color=np.stack([(xx*31+yy*7)%256,(xx*13+yy*23)%256,(xx*3+yy*43)%256],2).astype('uint8')
    result=[]
    for row in chosen:
        file=a.dataset/row['file'];source=np.asarray(Image.open(file).convert('RGB'));assert source.shape==(840,840,3)
        for variant in ['neutral','structured']:
            canvas=np.full((1000,1000,3),128,dtype='uint8') if variant=='neutral' else color.copy()
            canvas[70:910,80:920]=source;assert np.array_equal(canvas[70:910,80:920],source)
            ident=row['id']+'_'+variant;target=a.out/(ident+'.png');Image.fromarray(canvas).save(target)
            result.append(dict(id=ident,parent_id=row['id'],label=row['label'],variant=variant,file=target.name,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),original_file=str(file),original_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                roi=[80,70,840,840],source_dimensions=[1000,1000],original_pixels_retained=True))
    (a.out/'plan.json').write_text(json.dumps(dict(scope='SYNTHETIC_SURROUND_ENGINEERING_WITH_UNCHANGED_REAL_PHOTO_PIXELS_NOT_NEW_ACCURACY_TEST',
        images=result,source_selection_before_new_hardware_results=True,physical_whole_tile_coverage_established=False),indent=2),encoding='utf8');print(json.dumps(dict(cases=len(result))))
if __name__=='__main__':main()
