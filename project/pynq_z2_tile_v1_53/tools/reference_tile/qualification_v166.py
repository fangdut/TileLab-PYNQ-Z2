"""Conservative offline accuracy gate. Synthetic/reused data cannot qualify.

Identity and blind-test declarations require human source review; hashing
checks integrity, and does not independently prove those declarations.
Board acceptance is a separate gate; this offline prototype cannot pass it.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
from PIL import Image
import reference_tile as base
import reference_v166 as detector

GATES=dict(positive_physical_tiles_at_least=100,negative_physical_tiles_at_least=400,image_recall_wilson95_lower_at_least=.95,image_fpr_wilson95_upper_at_most=.01,negative_reject_wilson95_upper_at_most=.01,negative_alarm_or_reject_wilson95_upper_at_most=.01,minimum_positive_pixel_coverage=.80)

def wilson(success,total):
    if total==0:return [0.,1.]
    z=1.959963984540054;p=success/total;den=1+z*z/total;center=(p+z*z/(2*total))/den;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0.,center-half),min(1.,center+half)]

def metrics(rows):
    neg=[r for r in rows if r['label']=='good'];pos=[r for r in rows if r['label']=='crack']
    alarms=sum(r['alarm'] is True for r in neg);rejects=sum(r['alarm'] is None for r in neg)
    localized=sum(r['alarm'] is True and r['tp']>0 for r in pos)
    worst=min((r['pixel_coverage'] for r in pos),default=0.)
    m=dict(negative=len(neg),positive=len(pos),negative_alarms=alarms,negative_rejects=rejects,localized_positive=localized,positive_miss_or_reject=len(pos)-localized,minimum_positive_pixel_coverage=worst,image_recall_wilson95=wilson(localized,len(pos)),image_fpr_wilson95=wilson(alarms,len(neg)),negative_reject_wilson95=wilson(rejects,len(neg)),negative_alarm_or_reject_wilson95=wilson(alarms+rejects,len(neg)))
    m['gates']=dict(positive_count=len(pos)>=100,negative_count=len(neg)>=400,recall=m['image_recall_wilson95'][0]>=.95,fpr=m['image_fpr_wilson95'][1]<=.01,reject=m['negative_reject_wilson95'][1]<=.01,operational_failure=m['negative_alarm_or_reject_wilson95'][1]<=.01,crack_coverage=worst>=.80)
    m['passed']=all(m['gates'].values());return m

def validate(manifest,root):
    """Never silently exclude inadmissible samples from a claimed test set."""
    errors=[];root=Path(root).resolve()
    def check(condition,message):
        if not condition:errors.append(message)
    def file(name,digest):
        p=(root/name).resolve()
        check(p.is_relative_to(root),'Path escapes dataset root: '+name)
        if not p.is_file():errors.append('Missing file: '+name)
        else:check(base.sha(p)==digest,'SHA256 mismatch: '+name)
        return p
    check(manifest.get('schema')==1,'Unsupported evidence schema')
    check(manifest.get('scope')=='REAL_INDEPENDENT_SAME_PATTERN_BLIND_TEST','Evidence is not declared independent real same-pattern blind testing')
    check(manifest.get('frozen_implementation')==detector.implementation(),'Frozen implementation mismatch')
    check(manifest.get('frozen_policy_sha256')==base.hashlib.sha256(base.canonical(detector.policy())).hexdigest(),'Frozen policy mismatch')
    check(manifest.get('source_and_labels_reviewed') is True,'Human source/label review is missing')
    materials=manifest.get('materials',[]);check(bool(materials) and len(set(materials))==len(materials),'Declare unique supported pattern/material IDs')
    ids=set();pixels=set();references={};reference_units=set()
    for r in manifest.get('references',[]):
        try:
            check(r['material_id'] in materials,'Undeclared reference material')
            check(r['material_id'] not in references,'More than one reference per material')
            check(r['label']=='good' and r['real_photo'] is True,'Reference is not a reviewed real good photo')
            path=file(r['image'],r['sha256']);a=base.read_frame(path);key=base.hashlib.sha256(a.tobytes()).hexdigest();pixels.add(key)
            references[r['material_id']]=(a,r);reference_units.add(r['physical_tile_id'])
        except (KeyError,ValueError,OSError) as e:errors.append('Invalid reference: '+str(e))
    samples=manifest.get('samples',[]);check(bool(samples),'No real independent samples supplied')
    for r in samples:
        try:
            check(r['physical_tile_id'] not in ids,'Repeated physical tile in evaluation: '+r['physical_tile_id']);ids.add(r['physical_tile_id'])
            check(r['physical_tile_id'] not in reference_units,'Calibration tile reused for evaluation')
            check(r['material_id'] in references,'No matching good reference')
            check(r['label'] in ('good','crack'),'Unsupported sample label')
            check(r['real_photo'] is True and r['augmented'] is False and r['opened_for_tuning'] is False,'Synthetic, augmented or exposed sample: '+r['image'])
            path=file(r['image'],r['sha256']);a=base.read_frame(path);key=base.hashlib.sha256(a.tobytes()).hexdigest()
            check(key not in pixels,'Duplicate decoded image or reference self-comparison');pixels.add(key)
            if r['label']=='crack':
                maskpath=file(r['mask'],r['mask_sha256'])
                with Image.open(maskpath) as im:mask=np.array(im.convert('L'))
                check(mask.shape==(720,1280) and set(np.unique(mask)).issubset({0,255}),'GT must be native full-frame binary mask')
                if mask.shape==(720,1280):
                    check(bool(mask[110:610,390:890].any()),'No annotated crack in ROI');outside=mask.copy();outside[110:610,390:890]=0
                    check(not outside.any(),'Annotated crack outside supported ROI; do not silently crop GT')
        except (KeyError,ValueError,OSError) as e:errors.append('Invalid sample: '+str(e))
    return errors,references

def evaluate(manifest,root):
    errors,references=validate(manifest,root);rows=[]
    if not errors:
        for r in manifest['samples']:
            result,mask,_=detector.compare(references[r['material_id']][0],base.read_frame(Path(root)/r['image']))
            truth=np.zeros((500,500),bool)
            if r['label']=='crack':
                with Image.open(Path(root)/r['mask']) as im:truth=np.array(im.convert('L'))[110:610,390:890]>0
            tp=int((mask&truth).sum()) if mask is not None else 0
            rows.append(dict(image=r['image'],sha256=r['sha256'],physical_tile_id=r['physical_tile_id'],material_id=r['material_id'],label=r['label'],alarm=result['alarm'],status=result['status'],reason=result.get('reason'),tp=tp,gt_pixels=int(truth.sum()),pixel_coverage=tp/int(truth.sum()) if truth.any() else None))
    per_material={m:metrics([r for r in rows if r['material_id']==m]) for m in manifest.get('materials',[])}
    accuracy_passed=not errors and bool(per_material) and all(m['passed'] for m in per_material.values())
    return dict(version='V1.66',gates=GATES,evidence_errors=errors,per_material=per_material,accuracy_qualified=accuracy_passed,board_integrated=False,board_accepted=False,qualified=False,unconditional_blockers=['Reference algorithm and 3x3 window/DDR path are not integrated into the deployed FPGA; no physical board acceptance'],implementation=detector.implementation(),rows=rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();m=json.loads(a.manifest.read_text(encoding='utf8'));r=evaluate(m,a.manifest.parent)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf8') as f:f.write(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},ensure_ascii=False));raise SystemExit(0 if r['qualified'] else 3)

if __name__=='__main__':main()
