from pathlib import Path
import sys,json,hashlib,urllib.request,sqlite3
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';F=O/'review_ui';sys.path.insert(0,str(R/'host'))
from workstation import Records
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
fixture=read(F/'fixture.json');ui=read(F/'browser_observations.json');assert ui['passed'] and ui['explicit_new_submission']['dialog_closed']
expected_a='窗口 A 已复核：确认裂痕。仅测试独立副本。'
expected_b='窗口 B 已查看修订 2：保留争议，提交需复查。仅独立副本。'
for name in ('rejected_b','loaded_latest'):
    row=read(F/(name+'.json'))['record'];assert row['review_revision']==2 and row['review']=='confirmed_crack' and row['note']==expected_a
for name in ('after_b_explicit','stopped'):
    row=read(F/(name+'.json'))['record'];assert row['review_revision']==3 and row['review']=='needs_recheck' and row['note']==expected_b
dom=(F/'conflict_dom.txt').read_text(encoding='utf-8');assert '保存复核结论" [disabled]' in dom and '窗口 B 的旧页面草稿：待对照 A 的最新结论。' in dom
dom=(F/'reloaded_dom.txt').read_text(encoding='utf-8');assert '复核修订 2' in dom and '窗口 B 的旧页面草稿：待对照 A 的最新结论。' in dom
assert (F/'stop.request').exists()
for item in fixture['fixtures']:
    original=Path(item['source_project']);assert sha(original/'DELIVERY_MANIFEST.json')==fixture['source_manifest_sha256']
    for suffix,field in (('.png','image_sha256'),('_mask.png','mask_sha256')):
        for directory in (original/'review_records',F/'review_records',F/'pristine'):
            assert sha(directory/(item['id']+suffix))==item[field]
    # Original review metadata is still the finalized unreviewed board evidence.
    old=sqlite3.connect((original/'review_records/inspection.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:assert old.execute('SELECT status,note FROM events WHERE id=?',(item['id'],)).fetchone()==('pending','')
    finally:old.close()
r=Records(R);rows=r.all();checks=[]
try:
    assert len(rows)==10 and all(e['review_revision']==0 and e['note']=='' and e['review']=='pending' for e in rows)
    for e in rows:
        assert e['firmware_version']==0x11e00 and all(e[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
        with urllib.request.urlopen('http://127.0.0.1:8770/api/record?id='+e['id'],timeout=5) as f:
            assert f.headers['Cache-Control']=='no-store';assert json.load(f)==e
        for mask in (False,True):
            field='mask_sha256' if mask else 'image_sha256';url='http://127.0.0.1:8770/api/image?id='+e['id']+('&mask=1' if mask else '')
            with urllib.request.urlopen(url,timeout=5) as f:
                data=f.read();assert f.status==200 and f.headers['X-Archive-Integrity']=='sha256-verified' and f.headers['X-Archive-SHA256']==e[field]
            assert hashlib.sha256(data).hexdigest()==e[field]
            checks.append(dict(id=e['id'],mask=mask,sha256=e[field],bytes=len(data)))
    assert r.all()==rows
finally:r.db.close()
baseline=read(O/'review_baseline/summary.json');crashes=read(O/'review_process_exit/summary.json');assert baseline['counterexample_reproduced'] and crashes['passed']
result=dict(passed=True,board_records=len(rows),verified_http_images=len(checks),verified_http_records=len(rows),checks=checks,ui=ui,
    original_evidence_and_review_unchanged=True,board_review_unchanged=True,isolated_ui_server_stopped=True,baseline_counterexample_reproduced=True,
    abrupt_process_exits=crashes['case_count'],scope='Two browser tabs update only independent copies of real evidence. Current board records are read-only checked; process exits are host SQLite tests, not physical power loss.')
(O/'review_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('checks','ui')}))
