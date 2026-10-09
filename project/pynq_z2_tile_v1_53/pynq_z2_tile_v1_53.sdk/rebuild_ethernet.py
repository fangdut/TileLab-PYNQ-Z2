"""Reimport authored Ethernet sources and rebuild without altering BSP settings."""
from pathlib import Path
import vitis
ws=Path(__file__).resolve().parent
try:
    client=vitis.create_client();client.set_workspace(str(ws))
    app=client.get_component(name='hdmi_ethernet')
    app.import_files(from_loc=str(ws/'ethernet_sources'),dest_dir_in_cmp='src')
    app.build()
finally:
    vitis.dispose()
