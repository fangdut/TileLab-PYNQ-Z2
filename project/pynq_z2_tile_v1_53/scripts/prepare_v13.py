from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
old=root.with_name('pynq_z2_tile_v1_5')
assert root.name=='pynq_z2_tile_v1_5'
hashes={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('rtl','constraints','scripts','host') for p in (old/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.sv','.tcl','.py','.html','.xdc','.ps1','.bat') and '_deps' not in p.parts and 'runtime' not in p.parts}
(root/'reports/baseline_v12_hashes.json').write_text(json.dumps(hashes,indent=2))
for rel in ('host/runtime','host/__pycache__'):
 p=(root/rel).resolve();assert p.is_relative_to(root.resolve());shutil.rmtree(p,ignore_errors=True)
for rel in ('host/display.pid','host/workstation.pid'):
 (root/rel).unlink(missing_ok=True)
for folder in ('host','scripts','pynq_z2_tile_v1_5.sdk'):
 for p in (root/folder).rglob('*'):
  if p.is_file() and p.suffix in ('.py','.tcl','.bat','.ps1','.html','.c','.ld') and '_deps' not in p.parts:
   s=p.read_text(encoding='utf-8-sig');s=s.replace('pynq_z2_tile_v1_5','pynq_z2_tile_v1_5').replace('Tile V1.3','Tile V1.3').replace('programmed_v13','programmed_v13').replace('8770','8770')
   p.write_text(s,encoding='utf-8')
print('Preserved V1.2 hashes',len(hashes))
