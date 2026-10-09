"""Fixed-parameter NEW MCS2 RGB cross-material board holdout; no tuning."""
from pathlib import Path
import hashlib
import io
import json
import time
import traceback
import numpy as np
from PIL import Image
import board_v153_real as reg


def main():
    reg.WIDE=True
    R=reg.R;D=R/'data/independent_mcs2';O=R/'reports/v153/external_mcs2'
    O.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((D/'manifest.json').read_text(encoding='utf-8'))
    result=dict(passed=False,scope=manifest['independence'],limitations=manifest['limitations'],
                manifest_sha256=reg.sha(D/'manifest.json'),fixed_parameters=manifest['fixed_before_inspection'],
                programming=reg.programmed_proof(),items=[])
    reg.action('pause')
    deadline=time.monotonic()+20
    while reg.state()['busy']:
        assert time.monotonic()<deadline;time.sleep(.03)
    reg.action('disconnect')
    bridge=reg.EthernetBridge(reg.state()['board_address']);bridge.enhance=True;bridge.passes=4;bridge.wide_weak=True
    boot=result['programming']['record']['boot_id']
    try:
        initial=bridge.stats()
        assert initial['boot_id']==boot and initial['version']==reg.FIRMWARE
        reg.empty(bridge,90,4,boot);before=bridge.stats()
        for row in manifest['items']:
            index=row['index'];name=f'holdout_{index:03d}'
            request=reg.display(name);time.sleep(.18)
            for _ in range(12):
                frame,image,mask=reg.capture(bridge,90,boot)
                pixels=reg.rgb(image);identity=sum(int(pixels[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))
                if identity==0x7000+index:break
                bridge.ack(frame)
            else:raise AssertionError('Stale HDMI identity: '+name)
            a=pixels.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
            keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True
            expected=reg.wide_weak_mask(reg.valley(gray,8),reg.valley(gray,16),keep)
            bounds=reg.regions(expected)
            with Image.open(io.BytesIO(mask)) as pic:actual=np.asarray(pic.convert('L'))>0
            with Image.open(D/'hdmi'/f'{name}.png') as pic:source_rgb=np.asarray(pic.convert('RGB'))
            with Image.open(D/'truth'/f'{name}.png') as pic:truth=np.asarray(pic.convert('L'))>0
            measured=dict(index=index,source=row['source_name'],request_id=request,barcode=identity,
                          frame=frame,mask_mismatch=int((actual!=expected).sum()),
                          rgb_mismatch=int((pixels!=source_rgb).sum()),
                          boxes_exact=frame['boxes']==bounds['boxes'] and frame['region_areas']==bounds['areas'],
                          tp=int((actual&truth).sum()),fp=int((actual&~truth).sum()),fn=int((~actual&truth).sum()),
                          image_sha256=hashlib.sha256(image).hexdigest(),mask_sha256=hashlib.sha256(mask).hexdigest())
            # Windows/GPU HDMI color processing can transform file RGB. Never
            # mislabel this as byte-exact file transport: retain mismatch counts
            # and identify the source by frame code AND per-channel geometry.
            measured['source_channel_correlations']=[float(np.corrcoef(pixels[110:610,390:890,k].ravel(),source_rgb[110:610,390:890,k].ravel())[0,1]) for k in range(3)]
            measured['source_bytes_equal_after_hdmi']=measured['rgb_mismatch']==0
            measured['passed']=reg.profile_matches(frame,90,4) and measured['mask_mismatch']==0 and measured['boxes_exact'] and all(np.isfinite(v) and v>.97 for v in measured['source_channel_correlations'])
            result['items'].append(measured)
            assert measured['passed'],measured
            # Bounded representative evidence, rather than thousands of PNGs.
            if index in (0,5,11,23):
                (O/f'{name}_original.png').write_bytes(image);(O/f'{name}_mask.png').write_bytes(mask)
            bridge.ack(frame);reg.empty(bridge,90,4,boot)
            print(json.dumps(dict(index=index,alarm=frame['alarm'],pixels=frame['candidate_pixels'],exact=True)),flush=True)
        after=bridge.stats();tp=sum(x['tp'] for x in result['items']);fp=sum(x['fp'] for x in result['items']);fn=sum(x['fn'] for x in result['items'])
        result.update(samples=len(result['items']),crack_alarms=sum(x['frame']['alarm'] for x in result['items']),
                      pixel_recall=tp/(tp+fn),pixel_precision=tp/(tp+fp) if tp+fp else 0.,iou=tp/(tp+fp+fn),
                      error_deltas={k:(after[k]-before[k])&0xffffffff for k in reg.ERROR_FIELDS},before=before,after=after)
        result['source_rgb_warning']='File RGB differs from physical HDMI acquisition; color transformation is measured, its Windows/GPU cause is not yet isolated. Oracle uses acquired RGB, labels retain source geometry. Do not claim source-file byte preservation or a universal recipe.'
        assert not any(result['error_deltas'].values()) and after['boot_id']==boot and after['error_status']==0
        result['passed']=True  # Engineering consistency, NOT an accuracy threshold.
    except Exception:
        result['error']=traceback.format_exc();raise
    finally:
        bridge.close();reg.action('display',value='station_6')
        (O/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','samples','crack_alarms','pixel_recall','pixel_precision','iou','error_deltas')}))


if __name__=='__main__':main()
