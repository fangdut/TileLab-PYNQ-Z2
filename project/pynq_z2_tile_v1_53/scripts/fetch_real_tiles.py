"""Fetch licensed photographic MVTec tile samples; never execute downloaded data."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,urllib.request,time,hashlib,collections
R=Path(__file__).resolve().parents[1];D=R/'data/real_tiles'
BASE='https://huggingface.co/datasets/Voxel51/mvtec-ad/resolve/main/'
rows=[s for s in json.loads((D/'samples.json').read_text())['samples'] if s.get('category',{}).get('label')=='tile']
jobs=[];entries=[]
for n,s in enumerate(sorted(rows,key=lambda s:(s['split'],s['defect']['label'],s['filepath']))):
 label=s['defect']['label'];split=s['split'];ident=s['_id']['$oid']
 e=dict(id=ident,split=split,label=label,source_path=s['filepath'],image=f'images/{split}/{label}/{ident}.png')
 jobs.append((s['filepath'],e['image']))
 if 'defect_mask' in s:
  e['mask']=f'masks/{label}/{ident}.png';e['source_mask']=s['defect_mask']['mask_path'];jobs.append((e['source_mask'],e['mask']))
 entries.append(e)
def fetch(job):
 remote,local=job;p=D/local;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  for attempt in range(4):
   try:
    data=urllib.request.urlopen(BASE+remote,timeout=30).read()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Not PNG')
    p.write_bytes(data);break
   except Exception:
    if attempt==3:raise
    time.sleep(1+attempt*2)
 return local,hashlib.sha256(p.read_bytes()).hexdigest()
hashes={}
with ThreadPoolExecutor(max_workers=4) as pool:
 for i,f in enumerate(as_completed([pool.submit(fetch,j) for j in jobs]),1):
  local,digest=f.result();hashes[local]=digest
  if i%25==0:print(f'Downloaded and hashed {i}/{len(jobs)}',flush=True)
manifest=dict(dataset='MVTec AD tile',primary_source='https://www.mvtec.com/research-teaching/datasets/mvtec-ad',mirror='https://huggingface.co/datasets/Voxel51/mvtec-ad',license='CC BY-NC-SA 4.0',citation='Bergmann et al., MVTec AD, CVPR 2019; IJCV 2021',split_policy='Official train/test split preserved; test images not used for threshold selection',samples=entries,sha256=hashes,counts=dict(collections.Counter(e['split']+'/'+e['label'] for e in entries)))
(D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(D/'README.md').write_text('# MVTec AD 瓷砖真实照片测试集\n\n原作者：MVTec Software GmbH，Bergmann 等，CVPR 2019 / IJCV 2021。\n\n来源：https://www.mvtec.com/research-teaching/datasets/mvtec-ad\n\n下载镜像：https://huggingface.co/datasets/Voxel51/mvtec-ad\n\n许可：CC BY-NC-SA 4.0；适用于本项目的非商业研究与竞赛验证，商用需另行获得许可。完整许可见 license.txt。\n\n保留官方训练与测试划分：训练集仅正常样本 230 张；测试集 117 张，含正常 33 张、裂纹 17 张及其他缺陷 67 张。原图是实际拍摄照片；后续移动视频只是由照片合成的测试输入，不是工厂实拍流水线。\n\n所有文件校验值、分类与像素标注映射见 manifest.json。不得将测试结果直接等同于用户工厂的准确率。\n',encoding='utf-8')
print(json.dumps(manifest['counts']),flush=True)
