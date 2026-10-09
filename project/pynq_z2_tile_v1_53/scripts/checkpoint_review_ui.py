from pathlib import Path
import sys,json,urllib.request,hashlib,datetime
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/review_ui'
stage=sys.argv[1];assert stage in ('after_a','rejected_b','loaded_latest','after_b_explicit','stopped')
fixture=json.loads((O/'fixture.json').read_text(encoding='utf-8'));item=fixture['fixtures'][0]
with urllib.request.urlopen('http://127.0.0.1:8771/api/record?id='+item['id'],timeout=5) as f:row=json.load(f)
for suffix,field in (('.png','image_sha256'),('_mask.png','mask_sha256')):
    for root in (Path(item['source_project'])/'review_records',O/'review_records',O/'pristine'):
        assert hashlib.sha256((root/(item['id']+suffix)).read_bytes()).hexdigest()==item[field]
result=dict(stage=stage,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),record=row,all_original_and_copy_images_unchanged=True)
(O/(stage+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if stage=='stopped':(O/'stop.request').write_text('stop\n')
print(json.dumps(dict(stage=stage,id=row['id'],review=row['review'],note=row['note'],revision=row['review_revision']),ensure_ascii=False))
