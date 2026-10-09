from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
cases=[('quad_sim_console.log','QUAD HYSTERESIS PASS pixels=20736'),('quad_reset_console.log','QUAD MIDRASTER RESET PASS pixels=20736'),('quad_integrated_console.log','PASS DETECTION: 73728 exact pixels'),('official_legacy_console.log','PASS DETECTION: 19840 exact pixels')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for name,expected in cases:
 s=(O/name).read_text(encoding='utf-8-sig')
 assert expected in s and not any(t in s for t in ('Fatal:','ERROR:','cannot be opened for reading')),name
 checks.append(dict(log=name,pass_marker=expected,sha256=sha(O/name)))
for name in ('legacy_baseline_console.log','legacy_original_grid_mismatch.log'):
 assert 'Fatal: pixel n=11686 x=6 y=5 got=ffffff exp=ff0000 mode=7' in (O/name).read_text(encoding='utf-8-sig')
for name in ('legacy_baseline_grid_fixed_console.log','legacy_grid_fixed_console.log'):
 s=(O/name).read_text(encoding='utf-8-sig');assert 'PASS RESET:' in s and 'PASS FRAME CRC: 31' in s and 'Fatal:' not in s
sources={p.relative_to(R).as_posix():sha(p) for folder in ('rtl','sim','models') for p in (R/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.sv','.py','.mem') and '__pycache__' not in p.parts}
result=dict(passed=True,cases=checks,rtl_and_oracle_sha256=sources,extra_pixel_clocks=3308,extra_latency_us=3308/74.25,legacy_grid_oracle_reproduced_on_baseline=True,scope='Behavioral RTL with independent NumPy/zlib vectors; does not replace timing or physical-board verification')
(O/'simulation_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('rtl_and_oracle_sha256','cases')}))
