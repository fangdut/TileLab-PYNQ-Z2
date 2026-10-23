"""Fresh proven csim/synthesis/cosim/export flow after reopened-wrapper failure."""
from pathlib import Path
import ctypes,hashlib,json,os,subprocess,time,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=P/'experimental/texture_v170/hls/frozen/v170_hls70.cpp';frozen=source.with_name('v170_hls71.cpp');assert not frozen.exists() and not (W/'v170_hls71').exists();frozen.write_bytes(source.read_bytes())
tcl=P/'experimental/cache_split_v186/build_full_hls.tcl';assert not tcl.exists();tcl.write_text(tcl.with_name('build_hls.tcl').read_text().replace('v170_hls70.cpp','v170_hls71.cpp'))
state=W/'v186_hls71_full_pipeline.json';assert not state.exists();j=dict(scope='FRESH_COMPLETE_HLS_CACHE_SPLIT_RTL_NOT_BOARD',status='SOURCE_AND_MEMORY_PREFLIGHT',board_programmed=False,source_sha256=sha(source))
def save():state.write_text(json.dumps(j,indent=2)+'\n')
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','totalpage','availpage','totalvirtual','availvirtual','extended']]
try:
 save();c=json.loads((W/'v186_all_c01/summary.json').read_text());assert c['cases']==c['correct']==117 and c['all_grid_values_exact'] and c['all_original_size_masks_exact'] and c['source_sha256']==sha(source)==sha(frozen)
 files=list((W/'v186_all_c01').glob('*/result.bin'));assert len(files)==117
 for p in files:assert p.read_bytes()==(W/'v179_all_c05'/p.parent.name/'result.bin').read_bytes()
 assert json.loads((W/'v186_cache_negative01/summary.json').read_text())['passed']
 assert json.loads((W/'v186_continuation_failure_audit.json').read_text())['synthesis_unchanged']
 assert json.loads((W/'v185_physical_pipeline01.json').read_text())['status']=='FAILED_NO_PROMOTION'
 sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
 from check_normal_cache import inspect as cache_inspect
 from check_mac_recurrence import inspect as recurrence_inspect
 assert cache_inspect(W/'v170_hls70')['passed'] and recurrence_inspect(W/'v170_hls70')['all_banks_safe']
 deadline=time.monotonic()+3600
 while True:
  m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
  if m.available>7500*1024*1024 and m.availpage>16000*1024*1024:break
  if time.monotonic()>deadline:raise TimeoutError('Single full RTL memory gate not ready')
  time.sleep(10)
 j.update(status='FULL_HLS_STARTED',available_mb=m.available//1024//1024);save()
 env=os.environ.copy();env.update(TILE_PACKED_DETECTOR_HLS=str(W/'v170_hls71'),TILE_PACKED_DETECTOR_VECTORS=str(W/'v170_vectors08_wide'))
 for n in ['TILE_PACKED_SYNTH_ONLY','TILE_PACKED_SMALL_FIXTURE','TILE_PACKED_DETECTOR_SOURCE']:env.pop(n,None)
 with (W/'v170_hls71_console.log').open('w') as log:
  run=subprocess.run(['D:/2025.2/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(tcl)],env=env,stdout=log,stderr=subprocess.STDOUT)
 if run.returncode:raise RuntimeError('Fresh full HLS71 RTL/IP failed')
 j.update(status='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD',returncode=0);save()
except Exception as e:j.update(status='FAILED_NO_PROMOTION',error=repr(e));save();raise
print(json.dumps(j),flush=True)
