from pathlib import Path
import os,subprocess,json
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
env=os.environ.copy();env.update(TILE_PACKED_DETECTOR_HLS=str(W/'v170_hls70'),TILE_PACKED_DETECTOR_VECTORS=str(W/'v170_vectors08_wide'),TILE_PACKED_SYNTH_ONLY='1')
for n in ['TILE_PACKED_SMALL_FIXTURE','TILE_PACKED_DETECTOR_SOURCE']:env.pop(n,None)
with (W/'v170_hls70_console.log').open('w') as log:
    r=subprocess.run(['D:/2025.2/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(P/'experimental/cache_split_v186/build_hls.tcl')],env=env,stdout=log,stderr=subprocess.STDOUT)
print(json.dumps(dict(returncode=r.returncode,scope='SEGMENTED_NORMALIZATION_SYNTHESIS_ONLY_NOT_RTL_OR_BOARD')),flush=True)
raise SystemExit(r.returncode)
