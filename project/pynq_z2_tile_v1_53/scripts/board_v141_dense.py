"""Bounded physical dense-input regression. Requires freshly programmed V1.41.

Pauses/disconnects Station before taking exclusive board ownership. Restores
an empty HDMI input and leaves Station paused. No archive database writes.
"""
from pathlib import Path
from datetime import datetime, timezone
import io,json,time,traceback,zlib,sys
import numpy as np
from PIL import Image
from board_v141_real import (R, EthernetBridge, state, action, display, capture,
    empty, rgb, detect, regions, programmed_proof, FIRMWARE, ERROR_FIELDS, sha)
from board_v141_helpers import checked_pixels


def main():
    out=R/'reports/v141/dense_board'
    out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v141_dense.py','scripts/board_v141_real.py','scripts/board_v141_helpers.py',
           'host/tcp_transport.py','host/workstation.py','models/weak_reference.py','models/regions_reference.py',
           'data/conveyor/transport_noise.png','data/conveyor/station_6.png']
    before_hash={n:sha(R/n) for n in names}
    result=dict(passed=False,revision='V1.41',started_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=before_hash,programming=programmed_proof(),status_windows=[],captures=[],
        scope='Actual HDMI dense synthetic noise, full PL pipeline, DMA, TCP and CRC/reference checks',
        limitations=['Synthetic stress stimulus is not a detector accuracy benchmark.',
                    'Finite samples are not a worst-case throughput or long-term reliability guarantee.',
                    'No new human external-display confirmation.'])
    bridge=None;touched=False
    try:
        s=state();action('pause');touched=True;end=time.monotonic()+20
        while state()['busy']:
            if time.monotonic()>end:raise TimeoutError('Station still busy')
            time.sleep(.05)
        assert not state()['pending_operation'] and not state()['pending_confirmation']
        action('disconnect')
        bridge=EthernetBridge('169.254.200.10');bridge.enhance=True;bridge.passes=4;bridge.low_gate=False
        boot=result['programming']['record']['boot_id']
        assert bridge.stats()['version']==FIRMWARE and bridge.stats()['boot_id']==boot
        result['initial_drain']=empty(bridge,90,4,boot)
        result['before']=bridge.stats();host_before=state()['captures']
        # No image requests in these windows. This directly repeats the old failure.
        for source in ('station_6','transport_noise','station_6'):
            request=display(source);time.sleep(.35);before=bridge.stats()
            started=time.monotonic();time.sleep(2);after=bridge.stats();elapsed=time.monotonic()-started
            keys=('captured','frames','invalid','gaps','descriptor_crc_errors')
            delta={k:(after[k]-before[k])&0xffffffff for k in keys}
            row=dict(source=source,request_id=request,before=before,after=after,delta=delta,
                seconds=elapsed,captured_fps=delta['captured']/elapsed)
            result['status_windows'].append(row)
            assert 50<row['captured_fps']<70 and abs(delta['captured']-delta['frames'])<=2,row
            assert all(delta[k]==0 for k in ('invalid','gaps','descriptor_crc_errors')),row
        assert host_before==state()['captures'],'Station took images during direct test'
        result['host_captures_status_only']=[host_before,state()['captures']]
        result['status_drain']=empty(bridge,90,4,boot)
        display('transport_noise');time.sleep(.3)
        first_crc=None
        for mode in ('raw','rle','packed'):
            bridge.transport.compression=mode!='raw';bridge.transport.packed=mode=='packed'
            for attempt in range(2):
                frame,image,mask=capture(bridge,90,boot)
                check=checked_pixels(frame,image,mask,boot,FIRMWARE)
                pixels=rgb(image)
                with Image.open(io.BytesIO(mask)) as picture:actual=np.asarray(picture)>0
                expected,_=detect(Image.fromarray(pixels),threshold=90,passes=4)
                bounds=regions(expected)
                check.update(mask_mismatch=int(np.count_nonzero(actual!=expected)),
                    regions_match=frame['boxes']==bounds['boxes'] and frame['region_areas']==bounds['areas'] and frame['region_overflow']==bounds['overflow'])
                if first_crc is None:first_crc=frame['pixel_crc32']
                assert first_crc==frame['pixel_crc32'],'Static stress image changed between wire modes'
                assert check['mask_mismatch']==0 and check['regions_match'],check
                if mode=='packed':
                    assert frame['wire_codec']=='BGR24_MASK1',frame['wire_codec']
                    assert frame['wire_payload_bytes']==1280*720*3+(1280*720+7)//8
                if frame['wire_codec']=='RAW32':assert frame['wire_payload_bytes']==1280*720*4
                files={}
                if attempt==0:
                    for label,data in [('original',image),('mask',mask)]:
                        name=f'{mode}_{label}.png';(out/name).write_bytes(data);files[name]=sha(out/name)
                row=dict(requested_mode=mode,attempt=attempt,frame=frame,check=check,files_sha256=files)
                result['captures'].append(row)
                (out/'progress.json').write_text(json.dumps(result,indent=2)+'\n')
                bridge.ack(frame)
                print(json.dumps(dict(mode=mode,codec=frame['wire_codec'],frame=frame['frame_id'],pixels=frame['candidate_pixels'],request_ms=frame['request_ms'],wire_bytes=frame['wire_payload_bytes'],exact=True)),flush=True)
        result['final_drain']=empty(bridge,90,4,boot);result['after']=bridge.stats()
        result['error_deltas']={k:(result['after'][k]-result['before'][k])&0xffffffff for k in ERROR_FIELDS}
        assert not any(result['error_deltas'].values()) and result['after']['depth']==0,result['error_deltas']
        assert result['after']['boot_id']==boot and result['after']['version']==FIRMWARE and result['after']['error_status']==0
        assert before_hash=={n:sha(R/n) for n in names}
        result.update(passed=True,actual_codecs=sorted({c['frame']['wire_codec'] for c in result['captures']}),sources_unchanged=True)
    except Exception:
        result['error']=traceback.format_exc();raise
    finally:
        if bridge:bridge.close()
        if touched:
            try:action('display',value='station_6')
            except Exception:result['cleanup_error']=traceback.format_exc();result['passed']=False
        result['finished_at']=datetime.now(timezone.utc).isoformat()
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
