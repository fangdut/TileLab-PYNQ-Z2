"""Seal the independent 1.53.1 successor without touching accepted V1.53."""
from pathlib import Path
import hashlib,json,datetime,re
R=Path(__file__).resolve().parents[1];O=R/'reports/v1531'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    parent_path=R/'reports/accepted_baseline/V1_53_DELIVERY_MANIFEST.json'
    parent=json.loads(parent_path.read_text(encoding='utf-8'))
    current=R/'DELIVERY_MANIFEST.json'
    assert json.loads(current.read_text(encoding='utf-8'))['version']=='V1.53','Already revised; create a successor'
    expected={'host/workstation.py','host/benchmark.html','README.md','docs/TileLab_最终提交版_技术与教学手册.pdf','docs/TileLab_演示视频详细拍摄方案.pdf'}
    changed={n for n,h in parent['frozen_sha256'].items() if sha(R/n)!=h}
    assert changed==expected,changed
    log=(O/'host_tests.log').read_text(encoding='utf-8');assert re.search(r'Ran 438 tests',log) and 'OK (skipped=1)' in log
    motion=json.loads((O/'submission_motion/summary.json').read_text(encoding='utf-8'));assert motion['passed'] and motion['automatic_archives']==20
    assert not any(motion['error_deltas'].values())
    additions=['reports/accepted_baseline/V1_53_DELIVERY_MANIFEST.json','host/test_submission_validation.py','scripts/seal_submission_patch.py','scripts/board_submission_patch_acceptance.py','docs/tools/apply_submission_addendum.py']
    additions += [p.relative_to(R).as_posix() for p in (R/'docs/accepted_v153').glob('*.pdf')]
    additions += [p.relative_to(R).as_posix() for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.log','.png')]
    summary=dict(release='1.53.1',passed=True,scope='Validation page repair; unchanged detector and firmware',
        inherited_core_summary='reports/v153/final_validation_summary.json',parent_manifest_sha256=sha(parent_path),
        changed_parent_files=sorted(changed),host_tests=dict(total=438,passed=437,skipped=1,skip_reason='Optional native word-RLE decoder unavailable'),
        board_motion=dict(passed=motion['passed'],automatic_archives=20,unique_product_ids=motion['unique_product_ids'],measured_input_fps=motion['measured_input_fps'],source_center_error_max_px=motion['source_center_error_max_px'],error_deltas=motion['error_deltas']),
        browser_current_report_loaded=True,pdf_addendum_rendered_and_visually_reviewed=True,
        inherited_pdf_page_content_streams_unchanged=True,inherited_pdf_annotations_preserved=True,
        github_uploaded=False,recognition_scope='Calibrated selected texture; NOT universal or factory accepted',
        source_sha256={n:sha(R/n) for n in sorted(changed|set(additions))})
    save(O/'summary.json',summary);additions.append('reports/v1531/summary.json')
    manifest=dict(parent,version='V1.53.1',sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        parent_version='V1.53',parent_manifest_sha256=sha(parent_path),validation_summary='reports/v1531/summary.json',
        amendment_scope='Current validation report HTTP route, illustration routes, scope and async-cache explanation; no detector/protocol change',
        frozen_sha256={n:sha(R/n) for n in sorted(set(parent['frozen_sha256'])|set(additions))})
    save(current,manifest);print(json.dumps(dict(sealed=True,files=len(manifest['frozen_sha256']),release=manifest['version'])))
if __name__=='__main__':main()
