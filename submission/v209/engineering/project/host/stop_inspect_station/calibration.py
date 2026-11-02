"""Material/reference qualification records. This module performs no vision.

This is workstation verification of a deployed frozen reference, not CNN
training, automatic accuracy certification, or physical camera calibration.
"""
from pathlib import Path
import hashlib,json,uuid
from controller import utc

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(record=value,sha256=digest(value)),ensure_ascii=False,indent=2),encoding='utf8');temp.replace(path)

def load(path):
    envelope=json.loads(path.read_text(encoding='utf8'))
    if digest(envelope['record'])!=envelope['sha256']:raise ValueError('标定记录校验失败')
    return envelope['record']

def text(value,label,limit=160):
    if not isinstance(value,str) or not value.strip() or len(value.strip())>limit:
        raise ValueError(label+'不能为空且不能超出长度限制')
    return value.strip()

class Calibrations:
    def __init__(self,root,profiles):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.profiles={p['id']:dict(p) for p in profiles};self.materials={};self.runs={}
        for folder in self.root.iterdir():
            if folder.is_dir() and (folder/'material.json').is_file():
                m=load(folder/'material.json')
                if m['id']!=folder.name:raise ValueError('材质记录路径不匹配')
                self.materials[m['id']]=m
                runs=sorted((folder/'runs').glob('*.json')) if (folder/'runs').exists() else []
                for path in runs:
                    run=load(path)
                    if run['material_id']!=m['id'] or run['id']!=path.stem:raise ValueError('核验批次路径不匹配')
                    self.runs[run['id']]=run
    def create(self,name,profile_id,conditions,operator):
        if profile_id not in self.profiles:raise ValueError('请选择已部署的参照配置')
        m=dict(id=uuid.uuid4().hex,name=text(name,'材质名称',80),profile_id=profile_id,
               conditions=text(conditions,'拍摄条件',300),created_by=text(operator,'操作员',60),created_utc=utc(),
               profile_sha256=self.profiles[profile_id]['model_sha256'])
        save(self.root/m['id']/'material.json',m);self.materials[m['id']]=m;return m
    def validate_material(self,ident):
        if ident not in self.materials:raise ValueError('材质不存在')
        m=load(self.root/ident/'material.json')
        if m!=self.materials[ident]:raise ValueError('材质记录运行期间发生变化')
        profile=self.profiles.get(m['profile_id'])
        if not profile or profile['model_sha256']!=m['profile_sha256']:raise ValueError('参照已变化，请重新建立材质标定')
        return m
    def _save_run(self,run):save(self.root/run['material_id']/'runs'/(run['id']+'.json'),run)
    def start(self,material_id,connection,reason,force=False):
        m=self.validate_material(material_id)
        candidates=[r for r in self.runs.values() if r['material_id']==material_id]
        candidates.sort(key=lambda r:r['created_utc'])
        if candidates and not force:
            r=candidates[-1]
            if r['boot_identity']==connection['boot_identity'] and r['profile_sha256']==m['profile_sha256'] and not r['revoked']:
                self.validate_run(r['id']);return r
        r=dict(id=uuid.uuid4().hex,material_id=material_id,material_sha256=digest(m),profile_sha256=m['profile_sha256'],
               boot_identity=connection['boot_identity'],created_utc=utc(),reason=text(reason,'核验原因',240),
               checks=[],certificate=None,revoked=False,revoke_reason=None)
        self.runs[r['id']]=r;self._save_run(r);return r
    def validate_run(self,run_id):
        r=self.runs[run_id];stored=load(self.root/r['material_id']/'runs'/(run_id+'.json'))
        if stored!=r:raise ValueError('核验记录运行期间发生变化')
        m=self.validate_material(r['material_id'])
        if r['material_sha256']!=digest(m):raise ValueError('材质条件与核验记录不匹配')
        if r['certificate']:
            cert=r['certificate'];path=self.root/r['material_id']/'certificates'/(cert['id']+'.json')
            if load(path)!=cert or cert['checks_sha256']!=digest(r['checks']):raise ValueError('标定凭证或核验样本发生变化')
        return r
    def check_input_unused(self,run_id,source_sha):
        r=self.validate_run(run_id)
        if r['certificate'] or r['revoked']:raise ValueError('本批核验已封存或失效，请新建核验批次')
        if any(c['source_sha256']==source_sha for c in r['checks']):raise ValueError('同一图片不能重复计入标定或同时充当良品与缺陷')
    def record(self,run_id,cycle):
        r=self.validate_run(run_id);self.check_input_unused(run_id,cycle['source_sha256'])
        result=cycle['result'];review=cycle['review'];expected=0 if cycle['purpose']=='calibration_good' else 1
        if result['boot_identity']!=r['boot_identity'] or result['model_sha256']!=r['profile_sha256']:raise ValueError('核验结果与参照或启动编号不匹配')
        verdict={'good':0,'defect':1}.get(review['verdict'])
        c=dict(cycle_id=cycle['id'],source_sha256=cycle['source_sha256'],purpose=cycle['purpose'],expected_alarm=expected,
               result_id=result['id'],result_sha256=result['result_sha256'],fpga_alarm=result['pl_image_alarm'],
               review_id=review['id'],review_verdict=review['verdict'],operator=review['operator'],utc=utc(),
               matched=verdict==expected and result['pl_image_alarm']==expected)
        r['checks'].append(c);self._save_run(r);return c
    def freeze(self,run_id,connection,operator):
        r=self.validate_run(run_id)
        if r['revoked'] or r['certificate']:raise ValueError('本批已失效或已封存')
        if connection['boot_identity']!=r['boot_identity'] or connection['model_sha256']!=r['profile_sha256']:raise ValueError('标定时板端配置已变化')
        normal=sum(c['expected_alarm']==0 and c['matched'] for c in r['checks']);defects=sum(c['expected_alarm']==1 and c['matched'] for c in r['checks'])
        if normal<3 or defects<1 or any(not c['matched'] for c in r['checks']):
            raise ValueError('需要至少3张不同良品及1张已知缺陷全部核验一致；失败样本不能跳过')
        cert=dict(id=uuid.uuid4().hex,material_id=r['material_id'],run_id=run_id,material_sha256=r['material_sha256'],
                  profile_sha256=r['profile_sha256'],boot_identity=r['boot_identity'],checks_sha256=digest(r['checks']),
                  normal_checks=normal,defect_checks=defects,approved_by=text(operator,'操作员',60),approved_utc=utc(),
                  scope='WORKSTATION_REFERENCE_CHECK_NOT_INDEPENDENT_ACCURACY_OR_PHYSICAL_CAMERA_CALIBRATION')
        save(self.root/r['material_id']/'certificates'/(cert['id']+'.json'),cert);r['certificate']=cert;self._save_run(r);return cert
    def revoke(self,run_id,reason):
        if not run_id:return
        r=self.runs[run_id];r['revoked']=True;r['revoke_reason']=str(reason);self._save_run(r)
    def summary(self,run_id):
        if not run_id:return None
        r=self.validate_run(run_id);normal=sum(c['expected_alarm']==0 and c['matched'] for c in r['checks']);defects=sum(c['expected_alarm']==1 and c['matched'] for c in r['checks']);failed=sum(not c['matched'] for c in r['checks'])
        return dict(id=r['id'],normal_checks=normal,defect_checks=defects,failed_checks=failed,revoked=r['revoked'],
                    revoke_reason=r['revoke_reason'],certificate=r['certificate'],
                    ready_to_freeze=normal>=3 and defects>=1 and not failed and not r['certificate'] and not r['revoked'])
