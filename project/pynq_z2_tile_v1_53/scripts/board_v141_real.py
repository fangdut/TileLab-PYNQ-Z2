"""Actual V1.41 board regression over 50 historical HDMI photos.

Run only after V1.41 is programmed and its local Station/player are running.
This script pauses/disconnects the Station, controls HDMI input, directly reads
and ACKs board test frames, and leaves the Station paused. No automatic archive
rows are created. Historical photos are development regression, NOT blind data.
Importing this module performs no HTTP/board operations and creates no reports.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse
import hashlib
import io
import json
import time
import urllib.request

import numpy as np
from PIL import Image

R=Path(__file__).resolve().parents[1]
B=R.parent/'pynq_z2_tile_v1_5'
BASELINE=R.parent/'pynq_z2_tile_v1_24/reports/v124/real_board'
sys.path[:0]=[str(R/'host'),str(R/'models')]
from workstation import EthernetBridge
from weak_reference import detect
from regions_reference import regions

API='http://127.0.0.1:8770'
FIRMWARE=0x12900
CRC_FIELDS=('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')
ERROR_FIELDS=('gaps','invalid','dropped','ack_errors','descriptor_crc_errors')


def state():
    with urllib.request.urlopen(API+'/api/state?limit=1',timeout=10) as response:value=json.load(response)
    if value.get('revision')!='V1.41':raise RuntimeError('Refusing a Station other than V1.41')
    return value


def action(op,**fields):
    request=urllib.request.Request(API+'/api/action',data=json.dumps(dict(op=op,**fields)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)


def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def programmed_proof():
    marker=R/'reports/programmed_v141.json';data=marker.read_bytes();record=json.loads(data)
    if record.get('active_application')!='hdmi_ethernet' or type(record.get('boot_id')) is not int:
        raise AssertionError('An Ethernet programming proof with a boot identity is required')
    workspace=R/'pynq_z2_tile_v1_53.sdk'
    names=('system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf')
    actual={str(workspace/name):sha(workspace/name) for name in names}
    if any(record.get('sha256',{}).get(name)!=actual[str(workspace/name)] for name in names):
        raise AssertionError('Programmed artifact proof does not match the current bit/XSA/ELF')
    return dict(path=str(marker),marker_sha256=hashlib.sha256(data).hexdigest(),record=record,artifact_sha256=actual)


def source_hashes():
    files=[Path(__file__),B/'data/real_tiles/manifest.json',R/'data/real_tiles/hdmi_manifest.json']
    files.extend(R/'host'/name for name in ('workstation.py','tcp_transport.py','event_identity.py',
        'capture_health.py','dma_recovery.py','word_rle.py','packed_pixels.py','recipes.py','recipes.json'))
    files.extend(R/'models'/name for name in ('weak_reference.py','valley_reference.py','regions_reference.py'))
    return {str(path.resolve()):sha(path) for path in files}


def display(source):
    request_id=action('display',value=source)['request_id'];deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        status=state()['stimulus_status']
        if (status.get('ready') and status.get('identity_confirmed') and status.get('observed')==source
                and status.get('observed_request_id')==request_id):
            return request_id
        time.sleep(.03)
    raise TimeoutError('HDMI player did not adopt request '+source)


def capture(bridge,threshold,boot):
    frame,image,mask=bridge.capture(threshold)
    if frame.get('firmware_version')!=FIRMWARE or frame.get('boot_id')!=boot:
        raise AssertionError('Board firmware/boot changed during regression; frame not ACKed')
    if not all(frame.get(key) is True for key in CRC_FIELDS):
        raise AssertionError('Missing one of the three frame integrity checks; frame not ACKed')
    return frame,image,mask


def profile_matches(frame,high,passes):
    word=frame['config_word']
    return ((word>>8)&255)==high and bool(word&(1<<24)) and bool(word&(1<<25))==(passes==4) and not word&(1<<26)


def empty(bridge,high,passes,boot):
    display('station_6');time.sleep(.35)
    drained=[]
    for _ in range(20):
        frame,_,_=capture(bridge,high,boot);bridge.ack(frame)
        drained.append(dict(event_id=frame['event_id'],frame_id=frame['frame_id'],config_word=frame['config_word']))
        if bridge.stats()['depth']==0 and profile_matches(frame,high,passes):return drained
    raise AssertionError('Failed to drain test queue and apply default-gate parameters')


def rgb(data):
    with Image.open(io.BytesIO(data)) as image:return np.asarray(image.convert('RGB'))


def run(legacy=False):
    high,passes=(89,2) if legacy else (90,4)
    out=R/'reports/v141'/('real_board_legacy' if legacy else 'real_board')
    out.mkdir(parents=True,exist_ok=False)  # Never overwrite earlier test evidence.
    result=dict(passed=False,scope='Actual V1.41 HDMI/PL/TCP historical development regression; not blind factory accuracy',
                firmware_version=FIRMWARE,high=high,low=(high+1)//2,support=3,passes=passes,
                low_gate=False,product_gate_sum=320,items=[],queue_drains=[])
    bridge=None;touched=False
    try:
        result['source_sha256']=source_hashes();result['startup_programmed_proof']=programmed_proof()
        source={item['id']:item for item in json.loads((B/'data/real_tiles/manifest.json').read_text())['samples']}
        items=[item for item in json.loads((R/'data/real_tiles/hdmi_manifest.json').read_text())['items'] if item['label'] in ('crack','good')]
        if len(items)!=50 or sum(item['label']=='crack' for item in items)!=17 or len({item['id'] for item in items})!=50:
            raise AssertionError('Expected the frozen 17 crack + 33 good historical dataset')
        for item in items:
            if not (BASELINE/f"real_{item['index']:03d}_original.png").is_file():raise FileNotFoundError('Missing finalized V1.24 RGB reference')
            if source[item['id']].get('mask') and not (B/'data/real_tiles'/source[item['id']]['mask']).is_file():raise FileNotFoundError('Missing ground-truth mask')
        write_json(out/'provenance.json',dict(source_sha256=result['source_sha256'],startup_programmed_proof=result['startup_programmed_proof']))
        state();action('pause');touched=True;deadline=time.monotonic()+20
        while state()['busy']:
            if time.monotonic()>deadline:raise TimeoutError('Station transfer did not finish after pause')
            time.sleep(.05)
        paused=state()
        if paused.get('pending_confirmation') or paused.get('pending_operation'):
            raise RuntimeError('Resolve the Station pending ACK/status before direct-board regression')
        action('disconnect')
        bridge=EthernetBridge('169.254.200.10');bridge.enhance=True;bridge.passes=passes;bridge.low_gate=False
        initial=bridge.stats();result['initial']=initial
        if initial['version']!=FIRMWARE:raise AssertionError('Expected freshly programmed V1.41 firmware')
        boot=initial['boot_id']
        if boot!=result['startup_programmed_proof']['record']['boot_id']:
            raise AssertionError('Connected board boot does not match the startup programmed proof')
        result['queue_drains'].append(empty(bridge,high,passes,boot))
        before=bridge.stats();result['before']=before
        for item in items:
            index=item['index'];command=f'real_{index:03d}';request_id=display(command);time.sleep(.18)
            skipped=[]
            for _ in range(6):
                frame,image,mask=capture(bridge,high,boot);pixels=rgb(image)
                identity=sum(int(pixels[22:38,1018+bit*14:1025+bit*14].mean()>128)<<bit for bit in range(16))
                if identity==0x6000+index:break
                skipped.append(dict(frame_id=frame['frame_id'],barcode=identity));bridge.ack(frame)
            else:raise AssertionError('HDMI frame identity mismatch for '+command)
            # Save the received test evidence before numerical checks or ACK.
            (out/f'{command}_original.png').write_bytes(image);(out/f'{command}_mask.png').write_bytes(mask)
            with Image.open(io.BytesIO(mask)) as picture:actual=np.asarray(picture)>0
            expected,_=detect(Image.fromarray(pixels),threshold=high,passes=passes);bounds=regions(expected)
            truth=np.zeros((720,1280),bool);sample=source[item['id']]
            if sample.get('mask'):
                with Image.open(B/'data/real_tiles'/sample['mask']) as label:
                    truth[110:610,390:890]=np.asarray(label.convert('L').resize((500,500),Image.Resampling.NEAREST))>0
            with Image.open(BASELINE/f'{command}_original.png') as old:baseline=np.asarray(old.convert('RGB'))
            row=dict(index=index,id=item['id'],label=item['label'],barcode=identity,request_id=request_id,
                     frame=frame,skipped_prior_frames=skipped,profile_match=profile_matches(frame,high,passes),
                     mismatch=int(np.count_nonzero(actual!=expected)),
                     expected_candidate_pixels=int(expected.sum()),candidate_pixels_match=frame['candidate_pixels']==int(expected.sum()),
                     boxes_match=frame['boxes']==bounds['boxes'] and frame['region_areas']==bounds['areas'] and frame['region_overflow']==bounds['overflow'],
                     baseline_rgb_mismatch=int(np.count_nonzero(pixels!=baseline)),
                     image_sha256=hashlib.sha256(image).hexdigest(),mask_sha256=hashlib.sha256(mask).hexdigest(),
                     baseline_rgb_sha256=sha(BASELINE/f'{command}_original.png'),
                     ground_truth_sha256=sha(B/'data/real_tiles'/sample['mask']) if sample.get('mask') else None,
                     tp=int((actual&truth).sum()),fp=int((actual&~truth).sum()),fn=int((~actual&truth).sum()))
            row['passed']=row['profile_match'] and row['mismatch']==0 and row['candidate_pixels_match'] and row['boxes_match'] and row['baseline_rgb_mismatch']==0
            result['items'].append(row);write_json(out/'progress.json',result['items'])
            print(json.dumps(dict(index=index,label=item['label'],alarm=frame['alarm'],pixels=frame['candidate_pixels'],exact=row['passed'])),flush=True)
            if not row['passed']:raise AssertionError('Profile/mask/regions/RGB regression failed; frame not ACKed')
            bridge.ack(frame);result['queue_drains'].append(empty(bridge,high,passes,boot))
        after=bridge.stats();crack=[row for row in result['items'] if row['label']=='crack']
        tp=sum(row['tp'] for row in crack);fp=sum(row['fp'] for row in crack);fn=sum(row['fn'] for row in crack)
        counts={label:dict(total=sum(row['label']==label for row in result['items']),
                          alarms=sum(row['label']==label and row['frame']['alarm'] for row in result['items'])) for label in ('crack','good')}
        errors={key:(after[key]-before[key])&0xffffffff for key in ERROR_FIELDS}
        result.update(after=after,samples=len(result['items']),pixel_exact=sum(row['passed'] for row in result['items']),
                      counts=counts,tp=tp,fp=fp,fn=fn,pixel_recall=tp/(tp+fn),pixel_precision=tp/(tp+fp),error_deltas=errors)
        result['sources_unchanged']=all(sha(Path(path))==digest for path,digest in result['source_sha256'].items())
        result['programmed_artifacts_unchanged']=programmed_proof()==result['startup_programmed_proof']
        result['passed']=(len(result['items'])==50 and all(row['passed'] for row in result['items'])
                          and not any(errors.values()) and after['error_status']==0 and after['boot_id']==boot
                          and result['sources_unchanged'] and result['programmed_artifacts_unchanged']
                          and after['version']==FIRMWARE and counts['good']['alarms']==0 and counts['crack']['alarms']==17)
        if not result['passed']:raise AssertionError('Final board counters or historical alarm regression failed')
    except Exception as error:
        result.update(passed=False,error_type=type(error).__name__,error=str(error));raise
    finally:
        if bridge:bridge.close()
        if touched:
            try:action('display',value='station_6')
            except Exception as error:result['cleanup_error']=str(error);result['passed']=False
        write_json(out/'summary.json',result)
        print(json.dumps({key:value for key,value in result.items() if key not in ('items','before','after','initial','queue_drains')}),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--legacy',action='store_true')
    args=parser.parse_args()
    raise SystemExit(run(args.legacy))
