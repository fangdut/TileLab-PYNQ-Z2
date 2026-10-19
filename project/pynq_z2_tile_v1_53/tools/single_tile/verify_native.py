"""Differential integer check for the optional local accelerator, no images/training."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from detector import ROOT
from fine_integer_reference import predict
from fine_integer_native import NativeBoost
ap=argparse.ArgumentParser();ap.add_argument('--native-library',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
if a.out.exists():raise FileExistsError(a.out)
rng=np.random.default_rng(16420261019);x=rng.integers(0,256,(4096,14),dtype=np.uint8);rows=[]
for path in [ROOT/'models/v159_integer_model.json',*(ROOT/'models/oof_v159'/f'fold{i}.json' for i in range(3))]:
    model=json.loads(path.read_text());expected=predict(x,model);actual=NativeBoost(model,a.native_library).predict(x)
    if not np.array_equal(expected,actual):raise AssertionError('Native/NumPy integer mismatch: '+path.name)
    rows.append(dict(model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),vectors=len(x),exact=True))
proof=dict(scope='Offline native/NumPy integer differential verification, not board or accuracy',vectors=sum(r['vectors'] for r in rows),all_exact=True,library_sha256=hashlib.sha256(a.native_library.read_bytes()).hexdigest(),models=rows)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
