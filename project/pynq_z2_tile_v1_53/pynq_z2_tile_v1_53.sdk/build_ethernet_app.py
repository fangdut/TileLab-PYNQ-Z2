"""Rebuild the application against the already fully built, unchanged BSP."""
from pathlib import Path
import vitis,hashlib,json
ws=Path(__file__).resolve().parent
lib=ws/'hdmi_platform/export/hdmi_platform/sw/standalone_a9/lib'
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in lib.glob('*.a')}
assert before and 'liblwip220.a' in before
client=vitis.create_client()
try:
 client.set_workspace(str(ws));app=client.get_component(name='hdmi_ethernet')
 app.import_files(from_loc=str(ws/'ethernet_sources'),dest_dir_in_cmp='src')
 user=(ws/'hdmi_ethernet/src/UserConfig.cmake').read_text()
 assert 'set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)' in user and '-fno-builtin-memcpy' in user
 app.build()
 after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in lib.glob('*.a')};assert after==before
 (ws.parent/'reports/v132/app_bsp_unchanged.json').write_text(json.dumps(dict(passed=True,archive_sha256=after),indent=2))
finally:vitis.dispose()
