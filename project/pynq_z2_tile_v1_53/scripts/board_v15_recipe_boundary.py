"""A mid-product change must wait until the empty gap; evidence retains captured config."""
import board_v13_acceptance as t
import json,time
t.OUT=t.R/'reports/v15/recipe_boundary';t.OUT.mkdir(parents=True,exist_ok=True)
cal=t.R/'reports/v15/hdmi_calibration/calibration.json'
THRESHOLD=json.loads(cal.read_text())['threshold'] if cal.exists() else 105
RECIPE='mvtec_hdmi_v15' if cal.exists() else 'mvtec_tile_v15'
def sample():
    t.shot();return t.shot()
def threshold(s):return (s['frame']['config_word']>>8)&255
t.action('pause')
while t.state()['busy']:time.sleep(.05)
t.action('display',value='station_6');time.sleep(.35)
while t.action('status')['depth']:t.shot()
t.action('recipe',value='synthetic_v14');initial=sample();assert threshold(initial)==36
t.action('display',value='station_1');time.sleep(.4);old=sample();assert threshold(old)==36 and old['frame']['product_id']>0
t.action('recipe',value=RECIPE);during=[sample() for _ in range(3)];assert all(threshold(s)==36 for s in during)
assert all(s['frame']['recipe_id']=='synthetic_v14' for s in during)
t.action('display',value='station_6');time.sleep(.5)
for _ in range(6):
    changed=sample()
    if threshold(changed)==THRESHOLD:break
assert threshold(changed)==THRESHOLD and changed['frame']['recipe_id']==RECIPE
t.action('display',value='real_000');time.sleep(.4);new=sample();assert threshold(new)==THRESHOLD and new['frame']['product_id']!=old['frame']['product_id']
result=dict(passed=True,old_product=old['frame'],mid_product=[s['frame'] for s in during],empty_after_switch=changed['frame'],new_product=new['frame'])
(t.OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
t.action('display',value='station_6');time.sleep(.35)
while t.action('status')['depth']:t.shot()
t.action('disconnect');print(f'PASS recipe remains 36 throughout old product and changes to {THRESHOLD} in the empty gap; frame evidence matches actual config',flush=True)
