"""120 s continuous automatic product evidence acceptance, bounded archive."""
from pathlib import Path
import io,json,statistics,time,traceback
import numpy as np
from PIL import Image
from board_v153_helpers import Client,ROOT,ERRORS,FIRMWARE,write,wait_for,paused,adopted,checked_pixels,programmed_proof

def main():
    O=ROOT/'reports/v1531/submission_motion';O.mkdir(parents=True,exist_ok=False)
    c=Client('http://127.0.0.1:8770');boot=programmed_proof()['record']['boot_id']
    result=dict(passed=False,scope='120s real-photo synthetic conveyor; actual PL/TCP/PNG/archive; no physical camera or monitor human confirmation',observations=[],evidence=[])
    try:
        paused(c);c.ok('status');c.ok('display',value='station_6');time.sleep(.5)
        c.ok('recipe',value='mvtec_hdmi_wide_weak_v152');c.ok('wire_mode',value='packed');c.ok('preview_rate',value=2)
        c.ok('storage',mode='archive',max_archive_mib=64);c.ok('start')
        wait_for(c,lambda s:s['frame'] and s['frame']['config_word']&(1<<27) and not s['error'])
        before_ids={r['id'] for r in c.records()};before=c.state()['board_stats'];begun=time.monotonic()
        request=c.ok('display',value='real_video')['response']['request_id']
        wait_for(c,lambda s:adopted(s,'real_video',request))
        while time.monotonic()-begun<120:
            s=c.get('/api/live');assert not s['error'],s['error']
            stats=s['board_stats'];assert stats['version']==FIRMWARE and stats['boot_id']==boot and stats['error_status']==0
            assert stats['capture_health']['ready'] and not s['recovery']['active']
            result['observations'].append(dict(seconds=time.monotonic()-begun,captures=s['captures'],frames=stats['frames'],depth=stats['depth'],stats={k:stats[k] for k in ERRORS},motion=s['stimulus_status'].get('motion'),frame_id=(s['frame'] or {}).get('frame_id')))
            time.sleep(.5)
        c.ok('display',value='station_6');time.sleep(.5)
        wait_for(c,lambda s:s['board_stats']['depth']==0 and not s['pending_operation'] and not s['pending_confirmation'])
        paused(c);after=c.state()['board_stats'];new=[r for r in c.records() if r['id'] not in before_ids]
        assert len(new)>=12,('Too few automatic defective product evidence records',len(new))
        assert len({r['product_id'] for r in new})==len(new),'Duplicate product evidence'
        for row in new:
            assert row['reason']=='hardware_alarm' and row['selection']=='FPGA_PRODUCT_BEST_FRAME' and row['selection_full_tile'] and row['alarm']
            assert row['config_word']&(1<<27) and ((row['config_word']>>8)&255)==90
            original,mask=c.image(row,archived=True),c.image(row,True,True)
            check=checked_pixels(row,original,mask,boot,FIRMWARE)
            with Image.open(io.BytesIO(original)) as im:a=np.asarray(im.convert('RGB'))
            code=sum(int(a[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))
            positions=[(code*8-k*1440+500)%5760-500 for k in range(4)]
            tile=min(range(4),key=lambda k:abs(positions[k]+250-640))
            result['evidence'].append(dict(id=row['id'],product_id=row['product_id'],frame_id=row['frame_id'],source_frame=code,tile_index=tile,
                                           tile_left=positions[tile],source_center_error_px=abs(positions[tile]+250-640),
                                           reported_center_error_px=row.get('selection_center_error_px'),full_tile=row['selection_full_tile'],integrity=check))
        errors={k:(after[k]-before[k])&0xffffffff for k in ERRORS};assert not any(errors.values()),errors
        seconds=result['observations'][-1]['seconds']-result['observations'][0]['seconds']
        frame_delta=(result['observations'][-1]['frames']-result['observations'][0]['frames'])&0xffffffff
        assert 58<=frame_delta/seconds<=62,('Input frame rate',frame_delta/seconds)
        result.update(passed=True,automatic_archives=len(new),unique_product_ids=len(new),error_deltas=errors,
                      measured_input_fps=frame_delta/seconds,source_center_error_max_px=max(x['source_center_error_px'] for x in result['evidence']),
                      before=before,after=after)
        c.ok('storage',mode='preview',max_archive_mib=1024);c.ok('display',value='real_video');c.ok('start')
    except Exception:
        result['error']=traceback.format_exc();raise
    finally:write(O/'summary.json',result)
    print(json.dumps({k:result[k] for k in ('passed','automatic_archives','measured_input_fps','source_center_error_max_px','error_deltas')}))

if __name__=='__main__':main()
