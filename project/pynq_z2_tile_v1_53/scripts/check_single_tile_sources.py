"""Verify frozen detector source and the generated host/firmware fixture contract."""
from pathlib import Path
import hashlib,json,runpy,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from single_tile_profile import load
p=load(ROOT);model=json.loads((ROOT/'models/v159_frozen_profile.json').read_text())
for name,digest in model['source_sha256'].items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen detector source mismatch: '+name)
import generate_single_tile_profile
expected=generate_single_tile_profile.render(p)
if (ROOT/'pynq_z2_tile_v1_53.sdk/ethernet_sources/single_tile_profile.h').read_text()!=expected:raise ValueError('Generated firmware profile header is stale')
print(json.dumps(dict(frozen_sources_verified=len(model['source_sha256']),profile_id=p['profile_id'],profile_sha256=p['profile_sha256'],accuracy_qualified=False)))
