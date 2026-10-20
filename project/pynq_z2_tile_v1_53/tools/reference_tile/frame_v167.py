"""Host preparation + full-frame FPGA scoring; no claim of ARM preprocessing.

The frozen V166 input rejection and connected-component rules are unchanged.
Only the source of all score/strong/weak pixels moves to the DDR accelerator.
"""
from pathlib import Path
import hashlib,time
import numpy as np
import reference_tile as base
import reference_v166 as v166
import registration_v167
import photometric_v167

def policy():
    p=v166.policy();p.update(version='V1.67-boundary-reference',scope='SINGLE_PATTERN_REFERENCE_HOST_ALIGNMENT_PL_SCORE_HOST_COMPONENTS',registration_sampling='INDEPENDENT_FIXTURE_BOUNDARY_AXES_THEN_PATTERN_IDENTITY_ZERO_DRIFT_TIES',photometric_model='REFERENCE_INTENSITY_STRATIFIED_MEDIANS_AFFINE_OR_IDENTIFIABLE_OFFSET',photometric_estimation_inset_px=8,photometric_reference_flatness_span=8,inspection_inset_px=0,mask_completion='RAW_LOW_RESIDUAL_COMPONENTS_SEEDED_ONLY_BY_ALREADY_ACCEPTED_MASK_NO_NEW_IMAGE_ALARMS');return p

def implementation():
    return {name:base.sha(Path(__file__).with_name(name)) for name in ('frame_v167.py','registration_v167.py','photometric_v167.py','reference_v166.py','reference_tile.py')}

def calibrate(image,material_id,destination):
    if not material_id or len(material_id)>80:raise ValueError('Invalid pattern ID')
    from PIL import Image
    import json
    ref=base.read_frame(image);destination=Path(destination)
    if destination.exists():raise FileExistsError('Calibration revisions are immutable')
    destination.mkdir(parents=True);Image.fromarray(ref).save(destination/'reference.png');p=policy()
    record=dict(schema=3,material_id=material_id,reference_declaration='CALLER_IDENTIFIED_GOOD_NOT_AUTOMATICALLY_VERIFIED',source_image_sha256=base.sha(image),reference_sha256=base.sha(destination/'reference.png'),implementation_sha256=implementation(),policy=p,policy_sha256=hashlib.sha256(base.canonical(p)).hexdigest(),accuracy_qualified=False)
    record['bundle_sha256']=hashlib.sha256(base.canonical(record)).hexdigest();(destination/'calibration.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return record

def prepare(reference,current):
    started=time.perf_counter();p=policy()
    if reference.shape!=(720,1280,3) or current.shape!=reference.shape or reference.dtype!=np.uint8 or current.dtype!=np.uint8:raise ValueError('Expected native720p RGB uint8')
    result=dict(version='V1.67-host-prepared-FPGA-frame',scope='SINGLE_PATTERN_REFERENCE_HOST_ALIGNMENT_PL_SCORE_HOST_COMPONENTS',accuracy_qualified=False,board_integrated=False,roi=p['roi'],declared_roi_pixels=250000,inspected_pixels=0,alarm=None,manual_review_required=True,reference_array_sha256=hashlib.sha256(reference.tobytes()).hexdigest(),current_array_sha256=hashlib.sha256(current.tobytes()).hexdigest())
    def reject(reason):
        result.update(status='REJECTED_INPUT',decision='REVIEW_INPUT_OR_EXTENSIVE_SURFACE_CHANGE',reason=reason,preparation_seconds=time.perf_counter()-started)
        return result,None,None,None
    registration,error=registration_v167.register(reference,current,p);result['registration']=registration
    if error:return reject(error)
    x0,y0,x1,y1=p['roi'];yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
    aligned=np.clip(np.rint(base._sample(current,xx+registration['dx'],yy+registration['dy'])),0,255).astype(np.uint8)
    ref,transfer=base.matched_reference(reference,registration['dx'],registration['dy'],p);result['resampling_transfer']=transfer
    saturation=np.any((ref>8)&(ref<247)&((aligned<=1)|(aligned>=254)),axis=-1);result['new_saturation_fraction']=float(saturation.mean())
    if saturation.mean()>p['maximum_new_saturation_fraction']:return reject('new_clipping_or_specular_saturation')
    fit,error=photometric_v167.fit(ref,aligned,p);result['photometric']=fit
    if error:return reject(error)
    edge=base.edge_tolerance(reference,p);ep=np.pad(edge,1,mode='edge');edge=np.maximum.reduce([ep[j:j+500,i:i+500] for j in range(3) for i in range(3)])
    def rgb(a):
        a=a.astype(np.uint64);return (a[...,0]<<16)|(a[...,1]<<8)|a[...,2]
    packed=(rgb(ref)|(edge.astype(np.uint64)<<24)|(rgb(aligned)<<32)).astype('<u8')
    result.update(preparation_seconds=time.perf_counter()-started,paired_sha256=hashlib.sha256(packed.tobytes()).hexdigest(),status='PREPARED')
    return result,packed,aligned,dict(reference=ref,edge=edge)

def finish(result,words,proof):
    if result['status']!='PREPARED' or words.shape!=(500,500) or words.dtype!=np.uint32 or np.any(words&~np.uint32(1023)):raise ValueError('Invalid FPGA frame result')
    if not proof.get('output_crc_verified') or proof.get('paired_sha256')!=result['paired_sha256'] or proof.get('pl_id')!=0x16700601 or proof.get('firmware')!=0x16700:raise ValueError('FPGA score evidence does not match this prepared pair')
    p=policy();score=(words&255).astype(np.uint8);strong=(words&256)!=0;weak=(words&512)!=0
    result.update(board_integrated=True,inspected_pixels=250000,hardware=proof,residual=dict(median=float(np.median(score)),p90=float(np.percentile(score,90)),strong_fraction=float(strong.mean())))
    if result['residual']['median']>p['maximum_median_residual'] or result['residual']['p90']>p['maximum_p90_residual'] or strong.mean()>p['maximum_strong_fraction']:
        result.update(status='REJECTED_INPUT',decision='REVIEW_INPUT_OR_EXTENSIVE_SURFACE_CHANGE',reason='extensive_surface_change_or_unqualified_reference');return result,None
    mask,regions=base.components(weak,strong,p)
    initial_pixels=int(mask.sum())
    if initial_pixels:
        # Recover weak gaps only after an alarm has already qualified. This
        # cannot turn a previously clean/rejected image into a new alarm.
        completion_policy=dict(p,minimum_component_seeds=1)
        mask,regions=base.components(score.astype(np.int16)>p['low'],mask,completion_policy)
    result['completion']=dict(initial_pixels=initial_pixels,completed_pixels=int(mask.sum()),can_create_new_image_alarm=False)
    result.update(status='COMPARED',alarm=bool(regions),decision='REFERENCE_CHANGE_CANDIDATE' if regions else 'NO_REFERENCE_CHANGE_CANDIDATE',regions=regions,candidate_pixels=int(mask.sum()))
    return result,mask

def oracle(packed,fit):
    # Validation only. Production inspect never calls this function.
    a=packed.astype(np.uint64)
    def unpack(v):return np.stack([(v>>16)&255,(v>>8)&255,v&255],axis=-1).astype(np.uint8)
    ref=unpack(a);current=unpack(a>>32);edge=((a>>24)&255).astype(np.uint8)
    normal,*_=base.integer_difference(ref,current,fit['gain_q8'],fit['offset_integer'],edge)
    score,strong,weak=v166.window_metric(ref,normal,edge)
    return score.astype(np.uint32)|(strong.astype(np.uint32)<<8)|(weak.astype(np.uint32)<<9)
