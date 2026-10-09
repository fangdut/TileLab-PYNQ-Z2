"""Final thirty-second production-workstation soak; leave real video running."""
import json,time
import board_v13_acceptance as t
R=t.R;OUT=R/'reports/v15';cal=json.loads((OUT/'hdmi_calibration/calibration.json').read_text())
t.action('pause')
while t.state()['busy']:time.sleep(.05)
t.action('display',value='station_6');time.sleep(.4)
while t.action('status')['depth']:t.shot()
t.action('recipe',value='mvtec_hdmi_v15')
for _ in range(6):
 s=t.shot()
 if s['frame']['applied_threshold']==cal['threshold']:break
else:raise AssertionError('Final video recipe not applied')
before=t.action('status');start=t.state();t.action('display',value='real_video');t.action('start')
begun=time.monotonic();snapshots=[]
while time.monotonic()-begun<30:
 time.sleep(2);s=t.state();snapshots.append(dict(captures=s['captures'],error=s['error'],enabled=s['enabled'],frame=s['frame'],board_stats=s['board_stats']))
 if s['error'] or not s['enabled']:raise AssertionError('Live workstation stopped: '+s['error'])
end=t.state();after=end['board_stats']
result=dict(passed=end['captures']>start['captures']+100 and end['frame']['applied_threshold']==cal['threshold'] and all(after[k]==before[k] for k in ('gaps','invalid','dropped')),seconds=time.monotonic()-begun,before=before,after=after,start=start,end=end,snapshots=snapshots,capture_delta=end['captures']-start['captures'],scope='Actual production service, PNG/SQLite archival enabled; left running on real-photo motion video')
(OUT/'delivery_live_state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=result['passed'],capture_delta=result['capture_delta'],seconds=result['seconds'],before=before,after=after)),flush=True)
assert result['passed']
