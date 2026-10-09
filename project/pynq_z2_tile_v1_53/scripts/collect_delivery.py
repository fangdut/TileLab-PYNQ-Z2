from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
checks={}
for name,markers in {'small_sim_retry.log':['PASS DETECTION: 19840','PASS RESET:'],
                     'full_tile_sim.log':['PASS DETECTION: 27648000','PASS FRAME CRC: 30'],
                     'bbox_unit.log':['PASS BBOX:'],
                     'review_tests.log':['Ran 6 tests','OK']}.items():
    s=(ROOT/'reports'/name).read_text(errors='replace')
    assert not re.search(r'(?m)^(Fatal:|ERROR:)',s),name
    assert all(m in s for m in markers),name
    checks[name]='PASS'
assert json.loads((ROOT/'reports/native_monitor.json').read_text())['result']=='PASS'
checks['native_monitor']='PASS_WITH_MOCK_REGISTERS'
sdk=ROOT/(ROOT.name+'.sdk');needed=[sdk/'system.bit',sdk/'system.xsa',sdk/'system.ltx',sdk/'hdmi_monitor/build/hdmi_monitor.elf']
assert all(p.is_file() and p.stat().st_size for p in needed),'Build outputs missing'
report=(ROOT/'reports/timing_summary.rpt').read_text()
m=re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([\d.-]+)\s+([\d.-]+)\s+(\d+)\s+(\d+)\s+([\d.-]+)',report,re.S)
assert m,'Timing summary missing'
wns,tns,fail,ends,whs=m.groups();assert float(wns)>=0 and float(whs)>=0 and int(fail)==0
drc=(ROOT/'reports/drc.rpt').read_text();assert not re.search(r'\|\s*(Error|Critical Warning)\s*\|',drc)
util=(ROOT/'reports/utilization.rpt').read_text()
resources={}
for key in ['Slice LUTs','Slice Registers','Block RAM Tile','DSPs']:
    m=re.search(r'\|\s*'+re.escape(key)+r'\s*\*?\s*\|\s*([\d.]+)',util)
    resources[key]=float(m[1]) if m else None
artifact=dict(project=ROOT.name,status='OFFLINE_VERIFIED_BOARD_PENDING',
    product_status='FIRST_ITERATION_CAPTURE_AND_NETWORK_NOT_IMPLEMENTED',
    tests=checks,timing=dict(wns_ns=float(wns),whs_ns=float(whs),tns_ns=float(tns)),resources=resources,
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in needed],
    warnings='Read CDC and methodology reports; timing exceptions are inherited from the baseline and need further audit',
    baseline_archive_sha256='ef93cb4e6211c10a11243aef6fae391bb87ed151cb5749802a63253ab3272091')
(ROOT/'DELIVERY_MANIFEST.json').write_text(json.dumps(artifact,indent=2))
state=json.loads((ROOT/'PROJECT_STATUS.json').read_text());state['status']=artifact['status'];state['product_status']=artifact['product_status']
(ROOT/'PROJECT_STATUS.json').write_text(json.dumps(state,indent=2))
print(json.dumps(artifact,indent=2))
