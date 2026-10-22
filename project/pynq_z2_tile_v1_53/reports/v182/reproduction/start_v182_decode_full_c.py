from pathlib import Path
import subprocess
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020');py='D:/Vivado/TileLab_Runtime_V168/Scripts/python.exe'
with (W/'v182_decode_full_c.log').open('w') as f:
    subprocess.run([py,'-X','utf8',P/'tools/fpga_texture_v170/check_full_c.py','--source',P/'experimental/control_decode_v182/texture_control_decode.cpp',
        '--profile',W/'v170_fullint224','--image',W/'dataset_v168/images/test/crack/6621d769324f6e05d583835f.png','--out',W/'v182_full_c01'],stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run([py,'-X','utf8',P/'tools/fpga_texture_v170/validate_full_c.py','--dataset',W/'dataset_v168',
        '--profile',W/'v170_fullint224','--compiled-check',W/'v182_full_c01','--out',W/'v182_all_c01','--workers','4'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('V179_SEGMENTED_FULL_C_FINISHED_NOT_RTL_OR_BOARD',flush=True)
