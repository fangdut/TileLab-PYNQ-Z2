"""Mutate only the new bounded UI test copy; retain fault bytes before restore."""
from pathlib import Path
import json,sys,hashlib,time,sqlite3,argparse,re
R=Path(__file__).resolve().parents[1];O=(R/'reports/v132/archive_ui').resolve();sys.path.insert(0,str(R/'host'))
from workstation import atomic
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['corrupt_original','corrupt_mask','restore','snapshot','stop']);ap.add_argument('--index',type=int,default=0);ap.add_argument('--stage',default='checkpoint');a=ap.parse_args()
assert re.fullmatch('[a-z0-9_-]{1,80}',a.stage)
meta=json.loads((O/'fixture.json').read_text());assert 0<=a.index<len(meta['fixtures']);f=meta['fixtures'][a.index]
def sha(data):return hashlib.sha256(data).hexdigest()
def checked(relative):
    p=(O/relative).resolve();assert p.is_relative_to(O),'Test target escaped isolated root';return p
if a.mode.startswith('corrupt_'):
    suffix='_mask.png' if a.mode=='corrupt_mask' else '.png';field='mask_sha256' if a.mode=='corrupt_mask' else 'image_sha256'
    p=checked('review_records/'+f['id']+suffix);data=p.read_bytes();assert sha(data)==f[field],'Unexpected prior copy mutation'
    atomic(p,data+b'\nV129_ISOLATED_TEST_CORRUPTION\n')
elif a.mode=='restore':
    fault=checked('fault_bytes');fault.mkdir(exist_ok=True)
    for suffix,field in (('.png','image_sha256'),('_mask.png','mask_sha256')):
        p=checked('review_records/'+f['id']+suffix);source=checked('pristine/'+f['id']+suffix).read_bytes();assert sha(source)==f[field]
        current=p.read_bytes()
        assert current==source or current==source+b'\nV129_ISOLATED_TEST_CORRUPTION\n','Unknown bytes in fixture; refuse overwrite'
        if current!=source:checked('fault_bytes/'+a.stage+'_'+str(time.time_ns())+'_'+f['id']+suffix).write_bytes(current)
        atomic(p,source)
elif a.mode=='stop':checked('stop.request').write_text('stop')
db=sqlite3.connect(checked('review_records/inspection.sqlite3'));row=db.execute('SELECT status,note,payload FROM events WHERE id=?',(f['id'],)).fetchone();db.close()
result=dict(mode=a.mode,stage=a.stage,id=f['id'],review=row[0],note=row[1],stored=json.loads(row[2]),actual_image_sha256=sha(checked('review_records/'+f['id']+'.png').read_bytes()),actual_mask_sha256=sha(checked('review_records/'+f['id']+'_mask.png').read_bytes()))
checked(a.stage+'.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='stored'},ensure_ascii=False))
