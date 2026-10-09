from pathlib import Path
import time,json,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import action,state,wait_idle
wait_idle();action('display',value='station_6');action('threshold',value=255);action('wire_mode',value='rle');action('start')
end=time.monotonic()+10
while True:
 s=state()
 if s['frame'] and s['applied_threshold']==255 and s['board_stats']['depth']==0:break
 if time.monotonic()>end:raise TimeoutError('UI warmup failed')
 time.sleep(.1)
action('display',value='transport_noise');time.sleep(.7)
end=time.monotonic()+8
while True:
 s=state()
 if s['frame']['wire_codec']=='RAW32' and s['stimulus_status']['ready']:break
 if time.monotonic()>end:raise TimeoutError('Hard-to-compress RAW fixture not ready')
 time.sleep(.1)
assert not s['error'] and s['storage']['mode']=='preview'
(R/'reports/v132/wire_ui_before.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Real noise fixture ready in default latency mode; choose bandwidth option in UI')
