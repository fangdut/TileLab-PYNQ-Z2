"""Dataset provenance + content duplicate audit. Never treats repeated views as independent tiles."""
from pathlib import Path
import hashlib,json,collections
from PIL import Image,ImageOps
import numpy as np
R=Path(__file__).resolve().parents[1];B=R/'reports/v15/benchmark';d=json.loads((B/'results.json').read_text(encoding='utf-8'))
groups=collections.defaultdict(list);small=collections.defaultdict(list)
for s in d['items']:
    groups[s['sha256']].append((s['dataset'],s['id'],s['split']))
    im=ImageOps.exif_transpose(Image.open(s['source_image'])).convert('L').resize((17,16))
    a=np.asarray(im);h=np.packbits(a[:,1:]>a[:,:-1]).tobytes().hex();small[(s['dataset'],h)].append((s['id'],s['split']))
identical=[v for v in groups.values() if len(v)>1];similar=[v for v in small.values() if len(v)>1]
result=dict(photographs_downloaded=230+len(d['items']),evaluated_images=len(d['items']),calibration_images=230,exact_duplicate_groups=identical,exact_duplicate_extra_images=sum(len(v)-1 for v in identical),identical_256_bit_dhash_groups=len(similar),dhash_repeated_images=sum(len(v) for v in similar),dhash_cross_split_groups=sum(len(set(s[1] for s in v))>1 for v in similar),similarity_warning='Equal difference hashes are only a screening signal, not identity proof. Different hashes do not establish physical independence. Roof dataset explicitly has limited physical specimens. Do not infer factory generalization.',author_archive_sha256=hashlib.sha256((R/'data/ceramic_cracks_author.zip').read_bytes()).hexdigest(),license_scope={'mvtec':'CC BY-NC-SA 4.0, official research dataset','roof_ceramic':'CC BY 4.0, 1600 originals only; no 7000 augmentations','facade_ceramic':'No explicit repository license; local audit only, do not include original photos in redistributable project archive'})
(B/'dataset_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='exact_duplicate_groups'},ensure_ascii=False))
