"""Run only on an already-running V1.37 Station and HDMI player.

Two bounded, synthetic-source real-board comparisons. All image reception is
through the Station API; no second board connection is created. NumPy models
are used offline after each run is paused, never for live product decisions.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zlib

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'models'))
import numpy as np
from PIL import Image
from weak_reference import detect
from regions_reference import regions

BASE='http://127.0.0.1:8770'
OUT=ROOT/'reports/v137/dark_gate_board'
SECONDS=36
ERROR_FIELDS=('gaps','dropped','invalid','ack_errors','descriptor_crc_errors')
CRC_FIELDS=('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')
KINDS=('dark_good','dark_crack','bright_good','bright_crack')


def utc():return datetime.now(timezone.utc).isoformat()
def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def delta(after,before,key):return (after[key]-before[key])&0xffffffff


def state():
    with urllib.request.urlopen(BASE+'/api/state?limit=1',timeout=10) as response:value=json.load(response)
    assert value.get('revision')=='V1.37','Refusing a station other than V1.37'
    return value


def action(op,**fields):
    request=urllib.request.Request(BASE+'/api/action',data=json.dumps(dict(op=op,**fields)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)


def records():
    with urllib.request.urlopen(BASE+'/api/export?format=json',timeout=15) as response:return json.load(response)['records']


def picture(frame,mask=False,archived=False):
    key='id' if archived else 'frame'
    identity=frame['id'] if archived else str(frame['frame_id'])+'_'+frame['acquired_at']
    query=urllib.parse.urlencode({key:identity,'mask':int(mask)})
    with urllib.request.urlopen(BASE+'/api/image?'+query,timeout=10) as response:
        data=response.read()
        if archived:
            digest=hashlib.sha256(data).hexdigest()
            assert response.headers.get('X-Archive-Integrity')=='sha256-verified'
            assert response.headers.get('X-Archive-SHA256')==digest
            assert frame['mask_sha256' if mask else 'image_sha256']==digest
    return data


def adopted(value,source,request_id):
    p=value['stimulus_status']
    return p.get('ready') and p.get('identity_confirmed') and p.get('observed')==source and p.get('observed_request_id')==request_id


def healthy(value):
    assert not value['error'] and not value['recovery']['active'],value['error']
    assert value['board_stats']['version']==0x12500
    assert value['board_stats']['error_status']==0
    assert value['capture_health']['ready'] and not value['capture_health']['stale'],value['capture_health']


def wait_for(predicate,timeout=15,check_health=False):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=state()
        if check_health:healthy(value)
        if predicate(value):return value
        time.sleep(.05)
    raise TimeoutError('Station condition timeout: '+json.dumps(value,ensure_ascii=False))


def pause():
    action('pause')
    return wait_for(lambda value:not value['busy'])


def captured_profile(frame,low):
    return (frame.get('firmware_version')==0x12500 and frame.get('applied_threshold')==36
        and frame.get('weak_passes')==2 and bool(frame['config_word']&(1<<26))==low
        and frame.get('low_gate_enabled')==low and frame.get('applied_product_gate_sum')==(160 if low else 320)
        and frame.get('recipe_id')==('synthetic_dark_v137' if low else 'synthetic_v16')
        and frame.get('recipe_attribution')=='MATCHED_CAPTURED_THRESHOLD_GROWTH_AND_PRODUCT_GATE_NOT_REQUEST_TIME')


def decode_rgb(data):return np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))


def barcode(rgb):
    return sum(int(rgb[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))


def central_tile(code):
    assert 0<=code<720
    tiles=[]
    for index in range(4):
        x=((code*8-index*1440+500)%5760+5760)%5760-500
        if x<=640<x+500:tiles.append(dict(index=index,kind=KINDS[index],x=x))
    assert len(tiles)<=1
    return tiles[0] if tiles else None


def verify_pixels(frame,original,mask_data,low,require_full=False):
    rgb=decode_rgb(original);actual=np.asarray(Image.open(io.BytesIO(mask_data)).convert('L'))>0
    assert rgb.shape==(720,1280,3) and actual.shape==(720,1280)
    # Independently reassemble the archived/live RGB+mask as FPGA BGR+mask words.
    raw=np.empty((720,1280,4),np.uint8);raw[:,:,:3]=rgb[:,:,::-1];raw[:,:,3]=actual
    crc=zlib.crc32(raw.tobytes())
    expected,_=detect(rgb,threshold=36,passes=2);grouped=regions(expected)
    code=barcode(rgb);tile=central_tile(code)
    check=dict(frame_id=frame['frame_id'],source_barcode=code,
        crc3=all(frame.get(field) is True for field in CRC_FIELDS),reconstructed_pixel_crc_matches=crc==frame.get('pixel_crc32'),
        profile_matches=captured_profile(frame,low),mask_mismatch=int(np.count_nonzero(actual!=expected)),
        boxes_match=frame['boxes']==grouped['boxes'],areas_match=frame['region_areas']==grouped['areas'],
        overflow_match=frame['region_overflow']==grouped['overflow'],candidate_area_match=frame['candidate_pixels']==int(expected.sum()),
        full_tile=(bool(frame.get('selection_full_tile')) and tile is not None and 0<=tile['x']<=780) if require_full else None)
    check['passed']=(check['crc3'] and check['reconstructed_pixel_crc_matches'] and check['profile_matches']
        and check['mask_mismatch']==0 and check['boxes_match'] and check['areas_match'] and check['overflow_match']
        and check['candidate_area_match'] and (check['full_tile'] if require_full else True))
    return check,rgb,tile


def weighted_patch(rgb,tile):
    # Fixture crack begins at local x=120; this patch stays on intact surface.
    x=tile['x'];patch=rgb[150:210,x+30:x+90].astype(np.uint16)
    assert patch.shape==(60,60,3)
    weighted=patch[:,:,0]+2*patch[:,:,1]+patch[:,:,2]
    result=dict(region_xyxy=[x+30,150,x+89,209],pixel_count=int(weighted.size),
        rgb_min=patch.min(axis=(0,1)).tolist(),rgb_max=patch.max(axis=(0,1)).tolist(),
        rgb_mean=patch.mean(axis=(0,1)).tolist(),weighted_sum_min=int(weighted.min()),
        weighted_sum_max=int(weighted.max()),weighted_sum_median=float(np.median(weighted)),
        interpretation='Measured HDMI R+2G+B, not an assumption that RGB70 survived the desktop/display path unchanged.')
    result['within_low_but_below_legacy_gate']=result['weighted_sum_min']>=160 and result['weighted_sum_max']<320
    return result


def map_observations(observations,events,images):
    # Best-frame events can arrive later than a newer preview. Sort physical
    # FPGA frame IDs before unwrapping source periods; never use arrival order.
    codes={item['frame_id']:item['barcode'] for item in observations}
    for event in events:codes[event['frame_id']]=barcode(decode_rgb(images[event['id']][0]))
    cycles={};cycle=0;previous=None;observed_passes={}
    for frame,code in sorted(codes.items()):
        if previous is not None and code<previous:
            assert previous-code>360,('Nonmonotonic source frame without a period wrap',frame,previous,code)
            cycle+=1
        previous=code;cycles[frame]=cycle;tile=central_tile(code)
        if tile:
            identity=f'{cycle}:{tile["index"]}'
            observed_passes[identity]=dict(source_pass=identity,cycle=cycle,**tile)
    mapping=[]
    for event in events:
        code=codes[event['frame_id']];tile=central_tile(code)
        assert tile is not None and tile['index'] in (1,3),'Saved alarm did not map to a defective fixture tile'
        identity=f'{cycles[event["frame_id"]]}:{tile["index"]}'
        mapping.append(dict(record_id=event['id'],boot_id=event['boot_id'],product_id=event['product_id'],
            event_id=event['event_id'],frame_id=event['frame_id'],barcode=code,source_pass=identity,
            kind=tile['kind'],tile_index=tile['index'],tile_x=tile['x'],center_error_px=abs(tile['x']+250-640)))
    return list(observed_passes.values()),mapping


def run_case(low,run):
    name='low_gate_160' if low else 'legacy_gate_320'
    directory=run/name;directory.mkdir()
    result=dict(passed=False,name=name,low_gate=low,started_utc=utc(),requested_video_seconds=SECONDS)
    observations=[];samples=[];seen=set();proof=None
    events=[];images={};checks=[];event_images=[]
    try:
        pause();empty=action('display',value='station_6')['request_id']
        action('preview_rate',value=2);action('wire_mode',value='rle')
        action('storage',mode='archive',max_archive_mib=1024)
        # The low-gate recipe requires observed firmware capability before selection.
        action('status')
        action('recipe',value='synthetic_dark_v137' if low else 'synthetic_v16')
        count=state()['captures'];action('start')
        warm=wait_for(lambda value:value['captures']>count and adopted(value,'station_6',empty)
            and value.get('frame') and captured_profile(value['frame'],low)
            and value['board_stats']['depth']==0 and value['board_stats']['current_product_id']==0
            and not value['pending_operation'])
        healthy(warm);old={event['id'] for event in records()};before_state=state();before=before_state['board_stats']
        begun=time.monotonic();request=action('display',value='dark_video')['request_id'];adoption=None;last_print=begun
        while True:
            value=state();healthy(value);stats=value['board_stats'];elapsed=time.monotonic()-begun
            assert stats['boot_id']==before['boot_id']
            if adopted(value,'dark_video',request) and adoption is None:adoption=elapsed
            samples.append(dict(seconds=elapsed,queue_depth=stats['depth'],products_completed=stats['products_completed'],
                defective_products=stats['defective_products'],current_product_id=stats['current_product_id'],
                captures=value['captures'],received_bytes=value['transport_totals']['received_bytes']))
            frame=value.get('frame')
            if frame and adoption is not None:
                identity=(frame['frame_id'],frame['acquired_at'])
                if identity not in seen:
                    try:original=picture(frame)
                    except urllib.error.HTTPError as error:
                        if error.code!=404:raise
                    else:
                        seen.add(identity);rgb=decode_rgb(original);code=barcode(rgb)
                        if 0<=code<720:
                            assert captured_profile(frame,low)
                            tile=central_tile(code)
                            observations.append(dict(frame_id=frame['frame_id'],event_id=frame['event_id'],barcode=code,
                                product_id=frame.get('product_id'),alarm=frame['alarm'],selection=frame.get('selection'),
                                tile=tile,seconds=elapsed))
                            if (proof is None and tile and tile['index']==1 and 0<=tile['x']<=780
                                and frame['event_reason']==3 and frame.get('selection')=='LIVE_PREVIEW'
                                and frame['alarm'] and ((frame.get('product_id',0)>0) if low else frame.get('product_id')==0)):
                                try:mask=picture(frame,True)
                                except urllib.error.HTTPError as error:
                                    if error.code!=404:raise
                                else:proof=dict(frame=dict(frame),original=original,mask=mask)
            if elapsed>=SECONDS and stats['current_product_id']==0:
                assert adoption is not None
                break
            if elapsed>SECONDS+6:raise TimeoutError('No bounded product gap after 36 seconds')
            if time.monotonic()-last_print>=12:
                print(json.dumps(dict(case=name,seconds=round(elapsed,2),queue=stats['depth'],live_dark_proof=proof is not None)),flush=True)
                last_print=time.monotonic()
            time.sleep(.07)
        video_seconds=time.monotonic()-begun;empty=action('display',value='station_6')['request_id']
        wait_for(lambda value:adopted(value,'station_6',empty) and value['board_stats']['current_product_id']==0
            and value['board_stats']['depth']==0 and not value['pending_operation'],check_health=True)
        final=pause();healthy(final);seconds=time.monotonic()-begun;after=final['board_stats']
        assert after['boot_id']==before['boot_id'] and proof is not None,'No qualifying dark crack live sample'
        events=[event for event in records() if event['id'] not in old]
        evidence_directory=directory/'event_images';evidence_directory.mkdir()
        for index,event in enumerate(events):
            # Own numeric indices, never record-supplied text, form filenames.
            # Save each verified download immediately so later failures retain it.
            saved=dict(record_id=event['id'],event_id=event['event_id'],boot_id=event['boot_id'],
                       product_id=event.get('product_id'),files={},sha256={})
            event_images.append(saved)
            pair=[]
            for kind,is_mask in (('original',False),('mask',True)):
                data=picture(event,is_mask,archived=True)
                path=evidence_directory/f'{index:03d}_{kind}.png';path.write_bytes(data)
                digest=hashlib.sha256(data).hexdigest()
                assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
                assert digest==event['mask_sha256' if is_mask else 'image_sha256']
                saved['files'][kind]=path.relative_to(directory).as_posix();saved['sha256'][kind]=digest
                pair.append(data)
            original,mask=pair;images[event['id']]=(original,mask)
            check,_,_=verify_pixels(event,original,mask,low,require_full=True);check['record_id']=event['id'];checks.append(check)
        observed_passes,mapping=map_observations(observations,events,images)
        allowed=(0,1,2,3) if low else (2,3)
        expected_alarm_passes={item['source_pass'] for item in observed_passes if item['index'] in ((1,3) if low else (3,))}
        expected_product_passes={item['source_pass'] for item in observed_passes if item['index'] in allowed}
        actual_passes=[item['source_pass'] for item in mapping]
        alarm_counts=dict(Counter(item['kind'] for item in mapping))
        observed_counts=dict(Counter(item['kind'] for item in observed_passes))
        assert all(observed_counts.get(kind,0)>=3 for kind in KINDS),('Insufficient observed source passes',observed_counts)
        assert len(actual_passes)==len(set(actual_passes)) and set(actual_passes)==expected_alarm_passes
        assert alarm_counts.get('bright_crack',0)>=3
        assert alarm_counts.get('dark_crack',0)>=3 if low else alarm_counts.get('dark_crack',0)==0
        assert len({(e['boot_id'],e.get('product_id')) for e in events})==len(events)
        assert all(e.get('selection')=='FPGA_PRODUCT_BEST_FRAME' and e.get('product_id',0)>0 for e in events)
        assert all(check['passed'] for check in checks),checks
        error_deltas={key:delta(after,before,key) for key in ERROR_FIELDS};assert not any(error_deltas.values())
        assert delta(after,before,'defective_products')==len(events)
        assert delta(after,before,'products_completed')==len(expected_product_passes)
        assert not final['pending_operation'] and not final['pending_confirmation'] and after['depth']==0
        proof_check,proof_rgb,proof_tile=verify_pixels(proof['frame'],proof['original'],proof['mask'],low)
        luma=weighted_patch(proof_rgb,proof_tile)
        assert proof_check['passed'] and luma['within_low_but_below_legacy_gate']
        assert proof['frame']['alarm'] and proof['frame']['candidate_pixels']>0
        assert proof['frame']['product_id']>0 if low else proof['frame']['product_id']==0
        for kind in ('original','mask'):(directory/f'dark_live_{kind}.png').write_bytes(proof[kind])
        proof_result=dict(frame=proof['frame'],check=proof_check,measured_surface=luma,
            original='dark_live_original.png',mask='dark_live_mask.png',
            sha256={kind:hashlib.sha256(proof[kind]).hexdigest() for kind in ('original','mask')})
        write_json(directory/'dark_live_proof.json',proof_result)
        result.update(passed=True,boot_id=after['boot_id'],firmware_version=after['version'],seconds=seconds,
            video_seconds=video_seconds,player_adopted_after_seconds=adoption,before=before,after=after,
            error_deltas=error_deltas,host_captures=final['captures']-before_state['captures'],
            received_bytes_delta=final['transport_totals']['received_bytes']-before_state['transport_totals']['received_bytes'],
            saved_events=len(events),alarm_class_counts=alarm_counts,observed_source_class_counts=observed_counts,
            products_completed_delta=delta(after,before,'products_completed'),defective_products_delta=delta(after,before,'defective_products'),
            expected_alarm_source_passes=sorted(expected_alarm_passes),expected_tracked_source_passes=sorted(expected_product_passes),
            queue_peak_observed=max(item['queue_depth'] for item in samples),product_mapping=mapping,
            checks=checks,events=events,event_images=event_images,live_dark_proof=proof_result,observed_passes=observed_passes,
            observations=observations,samples=samples,final_state=final)
    except Exception:
        result.update(error=traceback.format_exc(),observations=observations,samples=samples,
                      events=events,event_images=event_images,checks=checks)
        # Retain a collected live sample even when a later assertion fails.
        if proof:
            for kind in ('original','mask'):(directory/f'dark_live_{kind}.png').write_bytes(proof[kind])
            write_json(directory/'dark_live_frame.json',proof['frame'])
        raise
    finally:
        cleanup=[]
        for operation in (pause,lambda:action('storage',mode='preview',max_archive_mib=1024),lambda:action('display',value='station_6')):
            try:operation()
            except Exception as error:cleanup.append(str(error))
        result['cleanup_errors']=cleanup
        if cleanup:result['passed']=False
        result['finished_utc']=utc();write_json(directory/'summary.json',result)
    assert result['passed'],result
    return result


def main():
    initial=state();assert initial['transport']=='ETHERNET_TCP'
    assert (initial.get('board_stats') or {}).get('version')==0x12500
    run=OUT/('run_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'));run.mkdir(parents=True)
    result=dict(passed=False,revision='V1.37',started_utc=utc(),run_directory=str(run),cases=[],
        scope='Actual HDMI/PL/TCP/Station observation of a controlled synthetic dark/bright source, not industrial detection accuracy.',
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('host/workstation.py','host/tcp_transport.py','host/recipes.py','host/recipes.json','host/ConveyorStimulus.cs',
             'models/weak_reference.py','models/regions_reference.py','scripts/board_v137_dark_gate.py','data/dark_gate/manifest.json')},
        limitations=['Synthetic 4-tile sequence repeats every 12 seconds; passes are not independent products.',
            'Source-pass mapping comes from captured HDMI barcodes and exact motion geometry, not elapsed time alone.',
            'Measured R+2G+B uses an intact captured surface patch; source RGB70 is not assumed to survive HDMI unchanged.',
            'No additional receiver, board programming or service startup is performed by this script.'])
    try:
        for low in (False,True):
            item=run_case(low,run);result['cases'].append(item);write_json(run/'progress.json',result)
            print(json.dumps({key:item[key] for key in ('name','passed','video_seconds','saved_events','alarm_class_counts','products_completed_delta')},ensure_ascii=False),flush=True)
        assert len({case['boot_id'] for case in result['cases']})==1
        result.update(passed=True,boot_id=result['cases'][0]['boot_id'],firmware_version=0x12500)
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        result['finished_utc']=utc();write_json(run/'summary.json',result);write_json(OUT/'summary.json',result)


if __name__=='__main__':main()
