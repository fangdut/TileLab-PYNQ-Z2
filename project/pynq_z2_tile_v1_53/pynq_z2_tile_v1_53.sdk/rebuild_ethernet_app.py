"""Rebuild software only after changes that do not alter XSA or BSP options."""
from pathlib import Path
import vitis
ws=Path(__file__).resolve().parent
c=vitis.create_client();c.set_workspace(str(ws))
a=c.get_component(name='hdmi_ethernet')
a.import_files(from_loc=str(ws/'ethernet_sources'),dest_dir_in_cmp='src')
p=ws/'hdmi_ethernet/src/UserConfig.cmake';p.write_text(p.read_text().replace('set(USER_COMPILE_OTHER_FLAGS )','set(USER_COMPILE_OTHER_FLAGS -fno-builtin-memcpy)'))
a.build()
vitis.dispose()
