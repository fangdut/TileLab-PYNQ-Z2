"""Copy selected source/assets only. The V1.5 baseline is read-only."""
from pathlib import Path
import shutil,json,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5'
assert R.name=='pynq_z2_tile_v1_53'
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for p in (B/'host').iterdir():
 if p.is_file() and p.suffix.lower() in ('.py','.html','.json','.ps1','.tcl','.bat','.cs','.txt') and p.name not in ('player_status.json','display_command.txt','dfx_runtime.txt'):
  copy(p,R/'host'/p.name)
src=B/'pynq_z2_tile_v1_5.sdk';dst=R/'pynq_z2_tile_v1_53.sdk'
for p in src.iterdir():
 if p.is_file() and p.suffix.lower() in ('.py','.bat','.tcl','.h','.c'):copy(p,dst/p.name)
shutil.copytree(src/'ethernet_sources',dst/'ethernet_sources',dirs_exist_ok=True)
for folder in ('conveyor','synthetic','real_tiles/hdmi','real_tiles/motion'):
 shutil.copytree(B/'data'/folder,R/'data'/folder,dirs_exist_ok=True)
for name in ('manifest.json','motion_frames.json','DATA_SOURCES.md','GENERATION_PROVENANCE.md','real_tiles/manifest.json','real_tiles/hdmi_manifest.json'):
 copy(B/'data'/name,R/'data'/name)
for p in B.glob('*.bat'):copy(p,R/p.name)
# Rename only inherited project-control files, not research scripts which read
# the explicitly preserved V1.5 dataset. Historical version comparisons stay.
for folder in ('host','pynq_z2_tile_v1_53.sdk'):
 for p in (R/folder).rglob('*'):
  if p.is_file() and p.suffix.lower() in ('.py','.html','.json','.ps1','.tcl','.bat','.cs','.txt','.h','.c'):
   s=p.read_text(encoding='utf-8-sig');s=s.replace('pynq_z2_tile_v1_5','pynq_z2_tile_v1_53').replace('programmed_v15','programmed_v132').replace('V1.5','V1.6').replace('1.5.1-storage','1.6.0-weak')
   p.write_text(s,encoding='utf-8')
for name in ('create_project.tcl','rebuild.tcl','add_capture.tcl'):
 p=R/'scripts'/name;p.write_text(p.read_text(encoding='utf-8-sig').replace('pynq_z2_tile_v1_5','pynq_z2_tile_v1_53'),encoding='utf-8')
p=dst/'ethernet_sources/event_queue.h';p.write_text(p.read_text().replace('0x00010500u','0x00010600u'))
p=dst/'ethernet_sources/main.c';p.write_text(p.read_text().replace('0x00f30007u','0x01f30007u'))
# The standalone .sdk is genuinely the Vitis workspace; it will be built from XSA.
(R/'host/storage_policy.json').write_text('{"mode":"preview","max_archive_mib":1024}')
baseline=json.loads((B/'DELIVERY_MANIFEST.json').read_text())
(R/'reports/weak_crack/baseline.json').write_text(json.dumps(dict(path=str(B),board_programming=baseline['programming'],data_policy='Original photos and old captures remain in V1.5; only reusable HDMI test textures copied. No bulk archives copied.'),indent=2))
print('V1.6 source workspace prepared; V1.5 untouched',flush=True)
