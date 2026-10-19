"""Build candidate ARM firmware in a NEW Vitis workspace, never program a board.

Run with Vitis 2025.2: vitis.bat -s scripts/build_support_software_v155.py
TILE_MEAN_WORKSPACE must name a new absolute .sdk directory.
TILE_MEAN_HARDWARE must contain the timing-approved candidate XSA and BIT.
The authored application remains <project>/<project>.sdk/ethernet_sources.
"""
from pathlib import Path
import hashlib,json,os,runpy,shutil,zipfile
R=Path(__file__).resolve().parents[1]
ws=Path(os.environ['TILE_MEAN_WORKSPACE'])
hardware=Path(os.environ['TILE_MEAN_HARDWARE'])
if not ws.is_absolute() or ws.suffix!='.sdk':raise ValueError('Choose a new absolute .sdk workspace')
if ws.exists():raise FileExistsError('Never overwrite a Vitis workspace')
status=(hardware/'implementation_status.txt').read_text()
values=dict(line.split('=',1) for line in status.splitlines() if '=' in line)
if float(values['setup_slack_ns'])<0 or float(values['hold_slack_ns'])<0:raise RuntimeError('Candidate timing has not passed')
author=R/'pynq_z2_tile_v1_53.sdk'
if '0x00012d00u' not in (author/'ethernet_sources/event_queue.h').read_text():raise RuntimeError('Wrong firmware source version')
for name in ('system.xsa','system.bit'):
    if not (hardware/name).is_file():raise FileNotFoundError(hardware/name)
with zipfile.ZipFile(hardware/'system.xsa') as archive:
    bits=[name for name in archive.namelist() if name.endswith('.bit')]
    if len(bits)!=1 or hashlib.sha256(archive.read(bits[0])).digest()!=hashlib.sha256((hardware/'system.bit').read_bytes()).digest():
        raise RuntimeError('XSA embedded BIT does not match the timing-approved standalone BIT; workspace creation blocked')
ws.mkdir()
for name in ('system.xsa','system.bit'):shutil.copy2(hardware/name,ws/name)
shutil.copytree(author/'ethernet_sources',ws/'ethernet_sources')
shutil.copy2(author/'build_ethernet.py',ws/'build_ethernet.py')
proof=dict(scope='Candidate software compilation, no programming or board acceptance',workspace=str(ws),
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ws/'ethernet_sources').iterdir() if p.is_file()},
    xsa_sha256=hashlib.sha256((ws/'system.xsa').read_bytes()).hexdigest())
(ws/'build_provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
runpy.run_path(str(ws/'build_ethernet.py'),run_name='__main__')
elf=ws/'hdmi_ethernet/build/hdmi_ethernet.elf'
if not elf.is_file():raise RuntimeError('Vitis did not produce ELF')
proof['elf_sha256']=hashlib.sha256(elf.read_bytes()).hexdigest();proof['compiled']=True
(ws/'build_result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(compiled=True,workspace=str(ws),elf_sha256=proof['elf_sha256'])))

