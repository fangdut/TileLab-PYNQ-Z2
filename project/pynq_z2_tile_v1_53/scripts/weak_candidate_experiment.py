"""One OFFLINE weak-threshold candidate; no live/board/source-data writes.

Output is the one authorized NEW V1.37 experiment directory below.
Exit 0 means the experiment completed, including a rejected candidate; inspect
result.json. Exit 1 means invalid input or an incomplete experiment. Parameters
are fixed in this script: no search, retry threshold, or automatic promotion.
Historical 230 normal + 17 crack + 33 good images are DEVELOPMENT material.
The declaration hashes all input bytes first; crack pixels/masks are decoded
only after all 230 normal images pass the gate. No image copies are generated.
"""
import sys
sys.dont_write_bytecode=True
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path

BASE=Path('D:/Vivado/pynq_z2_tile_v1_5')
MODEL=Path('D:/Vivado/pynq_z2_tile_v1_24/models')
EXPERIMENT=Path('D:/Vivado/pynq_z2_tile_v1_53/reports/v137/weak_candidate')
HIGH,BASE_LOW,CANDIDATE_LOW,PASSES,SUPPORT=90,45,34,4,3
MIN_RECALL_GAIN,MIN_PRECISION=.01,.98
EXPECTED_BASELINE=dict(crack_alarms=17,good_alarms=0,tp=24801,fp=339,fn=69242)


def digest(data):return hashlib.sha256(data).hexdigest()
def save(directory,name,value):
    with (directory/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(output):
    # This experiment is authorized only in the new V1.37 report directory.
    # Existing outputs and every old version remain immutable.
    output=Path(output)
    if not output.is_absolute():raise ValueError('--output must be an absolute new directory')
    output=output.resolve()
    if output!=EXPERIMENT.resolve():
        raise ValueError('Output must be the authorized V1.37 experiment directory')
    output.mkdir(parents=True,exist_ok=False)
    declaration=None;declaration_written=False
    try:
        files={}
        def register(path):
            path=Path(path).resolve();data=path.read_bytes();key=str(path)
            files[key]=dict(sha256=digest(data),bytes=len(data));return key,data
        manifest_path,manifest_bytes=register(BASE/'data/real_tiles/manifest.json')
        hdmi_path,hdmi_bytes=register(BASE/'data/real_tiles/hdmi_manifest.json')
        sources={sample['id']:sample for sample in json.loads(manifest_bytes)['samples']}
        items=[item for item in json.loads(hdmi_bytes)['items'] if item['label'] in ('crack','good')]
        if len(items)!=50 or sum(item['label']=='crack' for item in items)!=17:
            raise ValueError('Expected exactly the historical 17 crack + 33 good regression images')
        if len({item['id'] for item in items})!=50:raise ValueError('Duplicate regression identity')
        normal=[]
        for index in range(230):
            key,_=register(BASE/f'reports/v15/hdmi_calibration/calib_{index:03d}.png')
            normal.append(dict(id=f'normal_{index:03d}',image=key))
        regression=[];data_root=(BASE/'data/real_tiles').resolve()
        for item in items:
            index=item['index']
            if type(index) is not int or not 0<=index<=999:raise ValueError('Invalid HDMI manifest index')
            key,_=register(BASE/f'reports/v15/real_board/real_{index:03d}_original.png')
            sample=sources[item['id']];mask=None
            if item['label']=='crack':
                path=(data_root/sample['mask']).resolve()
                if not path.is_relative_to(data_root):raise ValueError('Mask path escaped the source data directory')
                mask,_=register(path)
            regression.append(dict(id=item['id'],label=item['label'],image=key,mask=mask))
        model_files=[register(MODEL/name)[0] for name in ('valley_reference.py','weak_reference.py','regions_reference.py')]
        script_path,_=register(Path(__file__))
        declaration=dict(created_at=utc(),scope='HISTORICAL DEVELOPMENT; not blind validation, factory accuracy, or board test',
            baseline=dict(high=HIGH,low=BASE_LOW,passes=PASSES,min_support=SUPPORT),
            candidate=dict(high=HIGH,low=CANDIDATE_LOW,low_formula='ceil(3*TH/8) = (3*TH+7)>>3',passes=PASSES,min_support=SUPPORT),
            gates=dict(normal_images=230,normal_alarms_allowed=0,stop_at_first_candidate_alarm=True,
                       regression_crack_alarms_required=17,regression_good_alarms_allowed=0,
                       min_absolute_pixel_recall_gain=MIN_RECALL_GAIN,min_crack_pixel_precision=MIN_PRECISION),
            expected_baseline=EXPECTED_BASELINE,roi=[80,80,1199,639],gt_placement=[390,110,500,500],
            scope_notes=['50 images previously used for architecture selection; no independent holdout claim',
                         'Reachability upper bound uses FOUR steps of an EIGHT-neighbor neighborhood, not a four-neighbor flood',
                         'Pixel precision/recall summary uses crack images, matching the historical reference; normal alarms reported separately',
                         'No threshold sweep; no model deployment; candidate eligibility means only eligibility for isolated RTL evaluation'],
            manifests=[manifest_path,hdmi_path],script=script_path,models=model_files,
            normal=normal,regression=regression,input_files=files)
        save(output,'declaration.json',declaration)  # Before any image is decoded/evaluated.
        declaration_written=True

        import numpy as np
        from PIL import Image
        sys.path.insert(0,str(MODEL))
        from valley_reference import valley
        from weak_reference import grow
        from regions_reference import regions
        def verify_code():
            for key in model_files+[script_path]:
                if digest(Path(key).read_bytes())!=files[key]['sha256']:raise ValueError('Experiment code changed: '+key)
        verify_code()
        roi=np.zeros((720,1280),bool);roi[80:640,80:1200]=True
        def image(path):
            data=Path(path).read_bytes()
            if digest(data)!=files[path]['sha256']:raise ValueError('Input changed after declaration: '+path)
            with Image.open(io.BytesIO(data)) as value:return value.copy()
        def score(path):
            with image(path) as photo:a=np.asarray(photo.convert('RGB'),dtype=np.int32)
            if a.shape!=(720,1280,3):raise ValueError('Historical capture must be 1280x720 RGB')
            return valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8)
        def detection(values,low):
            mask=(values>HIGH)&roi;weak=(values>low)&roi
            for _ in range(PASSES):mask=grow(mask,weak,SUPPORT)
            components=regions(mask)
            return mask,dict(alarm=bool(components['boxes'] or components['overflow']),candidate_pixels=int(mask.sum()),**components)
        def finish(status,eligible,**extra):
            verify_code()
            result=dict(completed=True,status=status,candidate_eligible_for_isolated_rtl=eligible,
                        production_changed=False,board_tested=False,completed_at=utc(),
                        declaration_sha256=digest((output/'declaration.json').read_bytes()),**extra)
            save(output,'result.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)
            return 0

        # No regression pixels or masks are decoded in this phase. An early
        # rejection is complete as a decision, but is not a 230-image evaluation.
        normal_rows=[]
        for sample in normal:
            values=score(sample['image']);_,base=detection(values,BASE_LOW);_,candidate=detection(values,CANDIDATE_LOW)
            normal_rows.append(dict(id=sample['id'],baseline=base,candidate=candidate))
            if base['alarm'] or candidate['alarm']:
                gate=dict(passed=False,images_checked=len(normal_rows),planned_images=230,complete_normal_sweep=len(normal_rows)==230,items=normal_rows)
                save(output,'normal_gate.json',gate)
                return finish('BASELINE_NORMAL_MISMATCH' if base['alarm'] else 'NORMAL_GATE_REJECTED',False,
                              normal_images_checked=len(normal_rows),regression_evaluated=False,first_failure=sample['id'])
            if len(normal_rows)%25==0:print(f'Normal gate {len(normal_rows)}/230: no alarms',flush=True)
        save(output,'normal_gate.json',dict(passed=True,images_checked=230,complete_normal_sweep=True,items=normal_rows))

        totals={name:dict(crack_alarms=0,good_alarms=0,tp=0,fp=0,fn=0) for name in ('baseline','candidate')};rows=[]
        for sample in regression:
            values=score(sample['image']);truth=np.zeros_like(roi)
            if sample['mask']:
                with image(sample['mask']) as label:
                    truth[110:610,390:890]=np.asarray(label.convert('L').resize((500,500),Image.Resampling.NEAREST))>0
            row=dict(id=sample['id'],label=sample['label'],results={})
            reachable=(values>HIGH)&roi
            for _ in range(PASSES):reachable=grow(reachable,roi,1)
            for name,low in (('baseline',BASE_LOW),('candidate',CANDIDATE_LOW)):
                mask,result=detection(values,low)
                if np.any(mask&~reachable):raise AssertionError('Bounded detector exceeded four-step seed reachability')
                result.update(tp=int((mask&truth).sum()),fp=int((mask&~truth).sum()),fn=int((~mask&truth).sum()))
                row['results'][name]=result;totals[name][sample['label']+'_alarms']+=int(result['alarm'])
                if sample['label']=='crack':
                    for key in ('tp','fp','fn'):totals[name][key]+=result[key]
            row['seed_reachability']=dict(gt_pixels=int(truth.sum()),gt_reachable_upper_bound=int((truth&reachable).sum()),
                gt_outside_four_steps=int((truth&~reachable).sum()),
                reachable_gt_score_35_to_45=int((truth&reachable&(values>34)&(values<=45)).sum()),
                reachable_background_score_35_to_45=int((~truth&reachable&(values>34)&(values<=45)).sum()))
            rows.append(row)
        for values in totals.values():
            values['pixel_recall']=values['tp']/(values['tp']+values['fn'])
            values['pixel_precision']=values['tp']/(values['tp']+values['fp']) if values['tp']+values['fp'] else 0.0
        old,new=totals['baseline'],totals['candidate']
        checks=dict(baseline_reproduced=all(old[key]==value for key,value in EXPECTED_BASELINE.items()),
                    no_crack_alarm_lost=new['crack_alarms']==17,normal_regression_zero=new['good_alarms']==0,
                    recall_gain_met=new['pixel_recall']-old['pixel_recall']>=MIN_RECALL_GAIN,
                    precision_floor_met=new['pixel_precision']>=MIN_PRECISION)
        eligible=all(checks.values())
        save(output,'regression.json',dict(scope='Historical development regression; not independent test',summary=totals,checks=checks,items=rows))
        return finish('ELIGIBLE_FOR_ISOLATED_RTL_ONLY' if eligible else 'REGRESSION_REJECTED',eligible,
                      normal_images_checked=230,regression_evaluated=True,regression_images=50,summary=totals,checks=checks)
    except Exception as error:
        save(output,'error.json',dict(completed=False,status='EXPERIMENT_ERROR',error_type=type(error).__name__,error=str(error),
                                     declaration_written=declaration_written,production_changed=False,board_tested=False))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    try:raise SystemExit(run(parser.parse_args().output))
    except Exception as error:print(type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(1)
