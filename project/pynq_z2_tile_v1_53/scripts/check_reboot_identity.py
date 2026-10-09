from pathlib import Path
import json,time
from board_v13_acceptance import action,shot,check,state,R
action('display',value='station_0');time.sleep(.5);shot()
action('display',value='station_4');time.sleep(.5);shot();s=shot();row=check(s,'demo_ready_double',2)
assert not s['error'] and s['board_stats']['depth']==0 and s['board_stats']['invalid']==0
f=s['frame'];key=f"pl_{f['boot_id']}_{f['event_id']}"
assert any(v['id']==key for v in s['records'])
row['archive_key']=key;row['board_stats']=s['board_stats']
p=R/'reports/board_acceptance/reboot_identity_checks.json'
rows=json.loads(p.read_text()) if p.exists() else []
assert f['boot_id'] not in {v['hardware']['boot_id'] for v in rows}
rows.append(row);p.write_text(json.dumps(rows,indent=2));print('REBOOT IDENTITY PASS: '+key,flush=True)
