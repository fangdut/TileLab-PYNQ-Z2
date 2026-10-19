"""Verify executed reference evidence matches source; never certifies accuracy."""
from pathlib import Path
import hashlib,inspect,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
from reference_tile import policy,canonical,integer_difference,sha
out=ROOT/'reports/v165';protocol=json.loads((out/'FINAL_PROTOCOL.json').read_text());proof=json.loads((out/'RTL_PROOF.json').read_text());vectors=json.loads((out/'pixel_vectors/manifest.json').read_text())
if hashlib.sha256(canonical(policy())).hexdigest()!=protocol['policy_sha256']:raise ValueError('Policy differs from executed reference audit')
for name,digest in protocol['source_sha256'].items():
    if sha(ROOT/'tools/reference_tile'/name)!=digest:raise ValueError('Executed reference source changed: '+name)
for name,digest in vectors['sha256'].items():
    if sha(out/'pixel_vectors'/name)!=digest:raise ValueError('Pixel vector mismatch')
if sha(ROOT/'experimental/reference_v165/rtl/reference_difference_v165.v')!=proof['rtl_sha256'] or sha(ROOT/'sim/tb_reference_difference_v165.sv')!=proof['testbench_sha256']:raise ValueError('Simulated RTL/testbench changed')
if hashlib.sha256(inspect.getsource(integer_difference).encode()).hexdigest()!=proof['oracle_function_sha256']:raise ValueError('Integer oracle changed')
print(json.dumps(dict(reference_audit_source_verified=True,pixel_vectors=8192,rtl_source_verified=True,accuracy_qualified=False,board_integrated=False)))
