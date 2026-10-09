"""Short observational run of the moving conveyor, not an industrial soak claim."""
import json,time,sys,argparse
from board_v13_acceptance import action,state,R,OUT
ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=int,default=96);ap.add_argument('--warmup',type=int,default=0);args=ap.parse_args()
if not 10<=args.seconds<=3600 or not 0<=args.warmup<=30:ap.error('seconds 10..3600; warmup 0..30')

action('pause')
while state()['busy']:time.sleep(.1)
if args.warmup:
 action('display',value='video');action('start');time.sleep(args.warmup);action('pause')
 while state()['busy']:time.sleep(.1)
before=action('status');captures=state()['captures'];records=len(state()['records'])
action('display',value='video');action('start');started=time.monotonic();samples=[]
while time.monotonic()-started<args.seconds:
 s=state();samples.append(dict(elapsed=round(time.monotonic()-started,2),captures=s['captures'],error=s['error'],frame=s['frame']))
 if s['error']:break
 time.sleep(2)
action('display',value='station_0');action('pause')
while state()['busy']:time.sleep(.1)
after=action('status');s=state();dt=time.monotonic()-started
result=dict(duration_seconds=dt,before=before,after=after,frames_delta=after['frames']-before['frames'],capture_delta=after['captured']-before['captured'],gap_delta=after['gaps']-before['gaps'],invalid_delta=after['invalid']-before['invalid'],dropped_delta=after['dropped']-before['dropped'],received_delta=s['captures']-captures,records_added=len(s['records'])-records,error=s['error'],samples=samples)
result['passed']=not result['error'] and result['invalid_delta']==0 and result['gap_delta']==0 and result['dropped_delta']==0 and result['received_delta']>0
result['warmup_seconds']=args.warmup
(OUT/'conveyor_observation.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2),flush=True)
sys.exit(0 if result['passed'] else 1)
