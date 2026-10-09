"""Same-pixel hardware/reference checks on six fixed real-photo inputs.
Known normal texture alarms remain failures of classification, not hidden.
"""
import board_v13_acceptance as t
import json,time
t.OUT=t.R/'reports/v14/real_board';t.OUT.mkdir(parents=True,exist_ok=True)
t.action('pause')
while t.state()['busy']:time.sleep(.05)
t.action('display',value='station_6');time.sleep(.4)
while t.action('status')['depth']:t.shot()
rows=[]
for n,label in [(0,'crack'),(1,'crack'),(35,'good'),(36,'good'),(17,'glue_strip'),(102,'rough')]:
 t.action('display',value=f'real_{n:03d}');time.sleep(.6);t.shot();s=t.shot()
 row=t.check(s,f'real_{n:03d}');row.update(truth=label,classification_correct=(s['frame']['alarm']==(label!='good')));rows.append(row)
 t.action('display',value='station_6');time.sleep(.3)
 while t.action('status')['depth']:t.shot()
 (t.OUT/'results.json').write_text(json.dumps(rows,indent=2))
t.action('disconnect')
print(json.dumps(dict(hardware_reference_checks=sum(r['passed'] for r in rows),samples=len(rows),normal_false_alarms=sum(r['truth']=='good' and r['hardware']['alarm'] for r in rows))),flush=True)
