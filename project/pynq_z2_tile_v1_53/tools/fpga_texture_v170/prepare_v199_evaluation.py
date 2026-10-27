"""Freeze file-disjoint public-photo audit, not a specimen-independent benchmark.

Normal calibration, diagnostic photos, and a reserved final set are selected
before any new inference. No synthetic images or outcome-driven selection.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--history',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    excluded=set();evidence=[]
    sources=[a.history/'v194_external01/catalog.json',a.history/'v195_dataset01/plan.json',a.history/'v195_dataset01/manifest.json',a.history/'v195_dataset02/plan.json',a.history/'v195_dataset02/manifest.json']
    def visit(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k in ['sha256','original_sha256','prepared_sha256'] and isinstance(v,str) and len(v)==64:excluded.add(v)
                else:visit(v)
        elif isinstance(obj,list):
            for v in obj:visit(v)
    for source in sources:
        assert source.is_file(),source
        visit(json.loads(source.read_text(encoding='utf8')));evidence.append(dict(path=str(source),sha256=sha(source)))
    train=json.loads((a.history/'v195_dataset01/published_train_normal_files.json').read_text())
    pools={label:json.loads((a.history/'v194_sources'/f'{label}_original_test_files.json').read_text()) for label in ['normal','defect']}
    rows=[];seen=set(excluded)
    def take(pool,label,role,count):
        picked=[]
        for row in sorted(pool,key=lambda r:hashlib.sha256(('v199-file-audit|'+r['id']).encode()).hexdigest()):
            c=row['content_details'];digest=c['sha256_hash']
            if digest in seen:continue
            seen.add(digest);picked.append(dict(id=row['id'],filename=row['filename'],label=label,role=role,url=c['download_url'],original_sha256=digest,bytes=c['size']))
            if len(picked)==count:break
        assert len(picked)==count,(label,role,len(picked));rows.extend(picked)
    take(train,'good','calibration',32)
    for label in ['normal','defect']:
        take(pools[label],'good' if label=='normal' else 'defect','diagnostic',12)
        take(pools[label],'good' if label=='normal' else 'defect','reserved_final',20)
    plan=dict(scope='FILE_DISJOINT_ROOF_CERAMIC_TRANSFER_AUDIT_NOT_FLOOR_OR_SPECIMEN_ACCEPTANCE',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source='https://data.mendeley.com/datasets/47x6jdbr5j/1',doi='10.17632/47x6jdbr5j.1',license='CC BY4.0',excluded_prior_hashes=len(excluded),prior_manifests=evidence,selected_before_new_inference=rows,baseline_model_sha256=sha(a.bundle/'verified_hdmi/model/model.bin'),preexisting_reference_sha256=sha(a.reference/'model.bin'),cnn_retraining=False,physical_specimen_independence=False,preparation='Offline whole-photo bilinear resize to720x720, explicitly derived camera input; not native high-resolution FPGA input',candidate_rule='Reuse the already frozen V195 R2 normal-reference bank; extend its threshold only with max(32 newly reserved normal calibration peaks)+1, never use diagnostic/final defect labels for threshold fitting',promotion_rule='Do not promote cross-material profiles into the generic station; original117 must remain exact for any transport-only replacement; report all confusion matrices without selecting successful subsets')
    (a.out/'plan.json').write_text(json.dumps(plan,indent=2));(a.out/'originals').mkdir();(a.out/'prepared').mkdir()
    def fetch(row):
        request=urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=90) as response:raw=response.read()
        assert hashlib.sha256(raw).hexdigest()==row['original_sha256'] and len(raw)==row['bytes']
        original=a.out/'originals'/(row['id']+'.jpg');original.write_bytes(raw)
        prepared=a.out/'prepared'/(row['id']+'.png')
        with Image.open(original) as im:
            size=list(im.size);im.convert('RGB').resize((720,720),Image.Resampling.BILINEAR).save(prepared)
        return dict(row,original='originals/'+original.name,file='prepared/'+prepared.name,original_dimensions=size,prepared_sha256=sha(prepared))
    images=list(ThreadPoolExecutor(max_workers=5).map(fetch,rows))
    assert len(images)==96 and len({r['original_sha256'] for r in images})==96
    manifest=dict(images=images,plan_sha256=sha(a.out/'plan.json'),file_disjoint_from_recorded_prior_data=True,physical_specimen_independence=False)
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(dict(images=len(images),roles={r:sum(x['role']==r for x in images) for r in ['calibration','diagnostic','reserved_final']},bytes=sum(x['bytes'] for x in images),manifest_sha256=sha(a.out/'manifest.json'))),flush=True)
if __name__=='__main__':main()
