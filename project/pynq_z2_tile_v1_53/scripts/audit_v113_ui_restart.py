from pathlib import Path
import json,hashlib,urllib.request
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
before=json.loads((O/'ui_restart_before.json').read_text(encoding='utf-8'))
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:s=json.load(f)
assert not s['error'] and not s['pending_operation'] and not s['enabled'] and not s['busy']
assert s['captures']==0 and s['records_total']==1 and s['transport_totals']['requests']==3
assert s['board_stats']['head']==before['pending']['frame']['event_id']
assert s['confirmation_journal']['history'][0]['status']=='ACKNOWLEDGED'
assert before['hashes']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'review_records').glob('*.png')}
(O/'ui_restart_after.json').write_text(json.dumps(dict(passed=True,no_recapture=True,requests=3,state=s),ensure_ascii=False,indent=2),encoding='utf-8')
print('Actual UI resumed pending event: status / ACK / status, zero new captures, original PNGs unchanged')
