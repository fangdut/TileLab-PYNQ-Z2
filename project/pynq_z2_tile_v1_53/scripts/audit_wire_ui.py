from pathlib import Path
import sys,json,time,hashlib,urllib.request
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import state
O=R/'reports/v132';phase=sys.argv[1];expected={'packed':'BGR24_MASK1','rle':'RAW32'}[phase]
end=time.monotonic()+8
while True:
 s=state()
 if s['wire_mode']==phase and s['frame']['wire_codec']==expected:break
 if time.monotonic()>end:raise TimeoutError('Actual UI request did not change the received codec')
 time.sleep(.1)
assert not s['error'] and s['enabled'] and s['capture_health']['ready'] and s['storage']['mode']=='preview' and s['records_total']==0
f=s['frame'];assert all(f[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert f['wire_payload_bytes']==(2880000 if phase=='packed' else 3686400)
key=str(f['frame_id'])+'_'+f['acquired_at']
with urllib.request.urlopen('http://127.0.0.1:8770/api/image?frame='+urllib.parse.quote(key),timeout=3) as r:image=r.read()
proof=dict(passed=True,phase=phase,state=s,png_sha256=hashlib.sha256(image).hexdigest())
(O/('wire_ui_'+phase+'.json')).write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
if phase=='rle':
 other=json.loads((O/'wire_ui_packed.json').read_text(encoding='utf-8'))
 assert other['png_sha256']==proof['png_sha256']
 assert other['state']['frame']['pixel_crc32']==f['pixel_crc32']
 (O/'wire_mode_ui.json').write_text(json.dumps(dict(passed=True,actual_ui_selection=True,full_png_identical=True,packed=other,latency=proof),ensure_ascii=False,indent=2),encoding='utf-8')
print('Actual UI mode and received codec agree; CRC valid; no archive growth:',phase)
