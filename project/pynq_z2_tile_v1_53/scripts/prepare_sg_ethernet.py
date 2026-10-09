from pathlib import Path
import shutil
r=Path(__file__).resolve().parents[1];ws=r/'pynq_z2_tile_v1_5.sdk'
shutil.copy2(ws/'ethernet_sources/sg_main.c.source',ws/'ethernet_sources/main.c')
print('Prepared authoritative V1.5 SG Ethernet application')
