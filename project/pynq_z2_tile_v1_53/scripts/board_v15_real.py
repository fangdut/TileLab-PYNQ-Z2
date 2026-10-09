"""All MVTec crack+good photographs through actual HDMI/PL/TCP, plus fixed stress examples."""
import board_v13_acceptance as t
import json,time
from pathlib import Path
t.OUT=t.R/'reports/v15/real_board';t.OUT.mkdir(parents=True,exist_ok=True)
cal=t.R/'reports/v15/hdmi_calibration/calibration.json'
THRESHOLD=json.loads(cal.read_text())['threshold'] if cal.exists() else 105
def empty():
    t.action('display',value='station_6');time.sleep(.35)
    while t.action('status')['depth']:t.shot()
def request(tvalue):
    t.action('threshold',value=tvalue)
    for _ in range(6):
        s=t.shot()
        if (s['frame']['config_word']>>8)&255==tvalue:return
    raise AssertionError('Requested threshold did not apply on empty belt')
t.action('pause')
while t.state()['busy']:time.sleep(.05)
empty();request(THRESHOLD);before=t.action('status')
items=json.loads((t.R/'data/real_tiles/hdmi_manifest.json').read_text())['items']
rows=[]
for item in items:
    if item['label'] not in ('crack','good'):continue
    n=item['index'];t.action('display',value=f'real_{n:03d}');time.sleep(.4);t.shot();s=t.shot()
    row=t.check(s,f'real_{n:03d}');row.update(truth=item['label'],source_id=item['id']);rows.append(row)
    empty();(t.OUT/'results.json').write_text(json.dumps(rows,indent=2))
after=t.action('status');result=dict(samples=len(rows),pixel_exact=sum(r['passed'] for r in rows),threshold=THRESHOLD,before=before,after=after,counts={label:dict(total=sum(r['truth']==label for r in rows),alarms=sum(r['truth']==label and r['hardware']['alarm'] for r in rows)) for label in ('crack','good')},scope='Actual HDMI PC display pipeline; masks compared against the RGB captured by FPGA, not assumed identical to source photographs',passed=all(r['passed'] for r in rows) and all(after[k]==before[k] for k in ('gaps','invalid','dropped')))
(t.OUT/'summary.json').write_text(json.dumps(result,indent=2));t.action('disconnect');print(json.dumps(result),flush=True)
assert result['passed']
