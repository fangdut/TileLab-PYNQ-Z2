"""Build a fresh transport app against a verified existing BSP (no bit change)."""
from pathlib import Path
import os,json,hashlib,shutil
import vitis
from model_identity import load_identity,require_hardware_support
root=Path(__file__).resolve().parents[2]
old=Path(os.environ['TILE_TEXTURE_BSP']);ws=Path(os.environ['TILE_TEXTURE_SW'])
hw=Path(os.environ['TILE_TEXTURE_HW']);model=Path(os.environ['TILE_TEXTURE_MODEL'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((old/'BUILD_RESULT.json').read_text());graph,model_header=load_identity(model)
model_capability_proof=require_hardware_support(hw,graph)
if sha(hw/'system.xsa')!=previous['xsa_sha256'] or sha(hw/'system.bit')!=previous['bit_sha256'] or sha(model/'model.bin')!=graph['sha256']:raise ValueError('Reused platform identity mismatch')
if ws.exists():raise ValueError('Use new workspace')
ws.mkdir();src=ws/'sources';src.mkdir()
for name in ['safe_memcpy.c','lscript.ld']:shutil.copy2(old/'sources'/name,src/name)
# A reused BSP says nothing about the new model CRC. Never copy its old header.
(src/'model_identity.h').write_text(model_header)
transport_source=Path(os.environ.get('TILE_TEXTURE_TRANSPORT_SOURCE',str(root/'experimental/texture_v170/firmware/main.c')))
shutil.copy2(transport_source,src/'main.c')
if b'#include "transport_crc32.h"' in transport_source.read_bytes():
    shutil.copy2(transport_source.parent/'transport_crc32.h',src/'transport_crc32.h')
profile_binding=None
if b'#include "profile_allowlist.h"' in transport_source.read_bytes():
    shutil.copy2(transport_source.parent/'profile_allowlist.h',src/'profile_allowlist.h')
    shutil.copy2(transport_source.parent/'profiles_binding.json',src/'profiles_binding.json')
    profile_binding=json.loads((src/'profiles_binding.json').read_text(encoding='utf8'))
    if profile_binding['candidate_source_sha256']!=sha(src/'main.c'):
        raise ValueError('Profile firmware binding source mismatch')
    if not (transport_source.parent/'xadapter_guarded.c').is_file():raise ValueError('Closed-loop transport requires guarded PHY transition')
    for name in ['xadapter_guarded.c','xemacpsif_physpeed_guarded.c','link_guard_proof.json']:
        shutil.copy2(transport_source.parent/name,src/name)
    guard=json.loads((src/'link_guard_proof.json').read_text())
    if guard['guarded_source_sha256']!=sha(src/'xadapter_guarded.c'):raise ValueError('PHY guard source mismatch')
    if guard['phy_guarded_source_sha256']!=sha(src/'xemacpsif_physpeed_guarded.c'):raise ValueError('PHY clock source mismatch')
shutil.copy2(hw/'system.xsa',ws/'system.xsa')
platform=old/'texture_platform/export/texture_platform/texture_platform.xpfm'
client=vitis.create_client()
try:
    try:client.set_workspace(str(ws))
    except Exception as e:
        if 'workspace version' not in str(e):raise
        client.update_workspace(str(ws))
    client.add_platform_repos(str(platform.parent))
    app=client.create_app_component(name='texture_transport',platform=str(platform),domain='standalone_a9',template='empty_application')
    app.import_files(from_loc=str(src),dest_dir_in_cmp='src')
    uc=ws/'texture_transport/src/UserConfig.cmake';s=uc.read_text();uc.write_text(s.replace('set(USER_COMPILE_OPTIMIZATION_LEVEL -O0)','set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)').replace('set(USER_COMPILE_OTHER_FLAGS )','set(USER_COMPILE_OTHER_FLAGS -fno-builtin-memcpy)'))
    app.build()
finally:vitis.dispose()
elf=ws/'texture_transport/build/texture_transport.elf'
result=dict(previous);result.update(elf_sha256=sha(elf),model_sha256=graph['sha256'],model_capability_proof=model_capability_proof,sources={p.name:sha(p) for p in src.iterdir()},
    reused_platform=str(platform),reused_platform_sha256=sha(platform),profiling='PS observes PL progress/timestamps only; no detection math')
if profile_binding:
    result.update(allowed_profiles=profile_binding['profiles'],profile_registry_sha256=profile_binding['registry_sha256'],profile_capability=0x2000c001)
(ws/'BUILD_RESULT.json').write_text(json.dumps(result,indent=2))
