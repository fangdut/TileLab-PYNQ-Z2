from pathlib import Path
import json,sys,shutil
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sys.path.insert(0,str(P/'scripts/texture_v170'));from verify_memory_layout import verify as memory;from verify_clock import verify as clock
out=P/'reports/v180/split125_preboard';out.mkdir(parents=True,exist_ok=False)
(out/'configuration.json').write_text(json.dumps(dict(scope='SAVED_SPLIT125_CONFIGURATION_NOT_PHYSICAL_OR_BOARD',memory=memory(W/'v180_hw01','split'),clock=clock(W/'v180_hw01',True),board_programmed=False),indent=2)+'\n')
dst=P/'reports/v180/target_flag_checks02';dst.mkdir(parents=True,exist_ok=False)
shutil.copy2(W/'v180_target_flag_checks02/summary.json',dst/'summary.json');shutil.copy2(W/'test_v180_target_flags01.py',dst/'reproduce.py')
repro=P/'reports/v180/reproduction';repro.mkdir(exist_ok=False)
for name in ['collect_v180_verified.py','prepare_v180_verified_collector.py','checkpoint_v180_pending01.py']:
    shutil.copy2(W/name,repro/name)
repro=P/'reports/v181/reproduction';repro.mkdir(parents=True,exist_ok=False)
for name in ['prepare_v181_residual01.py','start_v181_guarded_offline01.py','start_v181_residual_full_c.py','start_v181_hls63_synth.py']:
    shutil.copy2(W/name,repro/name)
print('ARCHIVED_PENDING_CONFIGURATION_AND_OFFLINE_SOURCES_NO_NEW_FPS_CLAIM')
