"""Audit independent failure fixtures and fresh board evidence served over HTTP."""
from pathlib import Path
import hashlib,json,urllib.request,sys,time
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';F=O/'archive_ui'
sys.path.insert(0,str(R/'host'))
from workstation import Records
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
fixture=read(F/'fixture.json');ui=read(F/'browser_observations.json')
assert ui['passed'] and ui['restored_submission']['dialog_closed']
prior='自动化复核测试副本；原工程证据未修改'
draft='V1.29 隔离副本测试：重试保留草稿；不改真实证据。'
for name in ('original_damaged','original_restored','after_open_mask_damaged','rejected_submission'):
    s=read(F/(name+'.json'));assert s['note']==prior and s['review']=='needs_recheck',name
for name in ('recovered_submission','final_restored'):
    s=read(F/(name+'.json'));assert s['note']==draft and s['review']=='needs_recheck',name
for item in fixture['fixtures']:
    original=Path(item['source_project']);assert sha(original/'DELIVERY_MANIFEST.json')==fixture['source_manifest_sha256']
    for suffix,field in (('.png','image_sha256'),('_mask.png','mask_sha256')):
        name=item['id']+suffix
        assert sha(original/'review_records'/name)==item[field]
        assert sha(F/'review_records'/name)==item[field]
        assert sha(F/'pristine'/name)==item[field]
assert (F/'stop.request').exists()
baseline=read(O/'archive_baseline/summary.json');assert baseline['counterexample_reproduced']
records=Records(R);rows=records.all();checks=[]
try:
    assert len(rows)==10,'Run the bounded real station acceptance first'
    for e in rows:
        assert e['firmware_version']==0x11d00 and all(e[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
        for mask in (False,True):
            field='mask_sha256' if mask else 'image_sha256'
            path=R/'review_records'/(e['id']+('_mask.png' if mask else '.png'))
            url='http://127.0.0.1:8770/api/image?id='+e['id']+('&mask=1' if mask else '')
            for repeat in range(2):
                t=time.perf_counter()
                with urllib.request.urlopen(url,timeout=5) as f:
                    data=f.read();headers=dict(f.headers)
                    assert f.status==200 and f.headers['Content-Type']=='image/png'
                    assert f.headers['Cache-Control']=='no-store'
                    assert f.headers['X-Archive-Integrity']=='sha256-verified'
                    assert f.headers['X-Archive-SHA256']==e[field]
                digest=hashlib.sha256(data).hexdigest()
                assert digest==e[field]==sha(path)
                checks.append(dict(id=e['id'],mask=mask,repeat=repeat,bytes=len(data),sha256=digest,milliseconds=(time.perf_counter()-t)*1000))
    assert records.all()==rows,'Read-only archive audit changed metadata'
finally:records.db.close()
result=dict(passed=True,board_records=len(rows),verified_http_reads=len(checks),checks=checks,ui=ui,
    isolated_fixture_scope=fixture['scope'],original_evidence_unchanged=True,isolated_images_restored=True,
    baseline_counterexample_reproduced=True,board_review_metadata_unchanged=True,
    limit='Failure injection uses isolated copies of real V1.28 evidence; fresh V1.29 board captures use read-only integrity checks.')
(O/'archive_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','ui')},ensure_ascii=False))
