"""Queue one full RTL run only if V183 physical fails, after safe RAM gate.

This is an active local experiment process, not a scheduled automation.
Successful V183 (even below10FPS) stops this queue for manual review.
"""
from pathlib import Path
import ctypes,hashlib,json,os,subprocess,time,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
source=P/'experimental/texture_v170/hls/frozen/v170_hls66.cpp';frozen=source.with_name('v170_hls67.cpp');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not frozen.exists() and not (W/'v170_hls67').exists();frozen.write_bytes(source.read_bytes())
tcl=P/'experimental/row_address_v184/build_full_hls.tcl';assert not tcl.exists();tcl.write_text(tcl.with_name('build_hls.tcl').read_text().replace('v170_hls66.cpp','v170_hls67.cpp'))
state=W/'v184_hls67_full_pipeline.json';assert not state.exists()
j=dict(scope='SOURCE_BOUND_ROW_ADDRESS_FULL_RTL_NOT_BOARD',status='WAITING_C_STATIC_PHYSICAL183_AND_RAM',source_sha256=sha(source),board_programmed=False)
def save():state.write_text(json.dumps(j,indent=2)+'\n')
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','totalpage','availpage','totalvirtual','availvirtual','extended']]
try:
 save();deadline=time.monotonic()+7200
 c=json.loads((W/'v184_all_c01/summary.json').read_text());assert c['cases']==c['correct']==117 and c['all_grid_values_exact'] and c['all_original_size_masks_exact'] and c['source_sha256']==sha(source)==sha(frozen)
 complete=list((W/'v184_all_c01').glob('*/result.bin'));assert len(complete)==117
 for p in complete:assert p.read_bytes()==(W/'v179_all_c05'/p.parent.name/'result.bin').read_bytes()
 for name in ['v184_bounds02/summary.json','v184_structure_negative01/summary.json','v184_row_unit_rtl01/summary.json']:
  assert json.loads((W/name).read_text())['passed']
 recurrence=json.loads((W/'v184_recurrence66.json').read_text());assert recurrence['all_banks_safe'] and recurrence['source_sha256']==sha(source)
 sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
 from check_row_address import inspect
 assert inspect(W/'v170_hls66')['source_sha256']==sha(source)
 while True:
  physical=json.loads((W/'v183_physical_pipeline01.json').read_text())
  if physical['status']=='EXPERIMENT_COMPLETE_REVIEW_ACTUAL_SPEED_BEFORE_PROMOTION':
   j.update(status='SKIPPED_V183_FINISHED_REVIEW_BOARD_RESULT_FIRST',physical_result=physical['board_result_review']);save();sys.exit(0)
  if physical['status']=='FAILED_NO_PROMOTION':break
  if time.monotonic()>deadline:raise TimeoutError('Physical183 not finished; full RTL remains blocked')
  time.sleep(10)
 j.update(status='WAITING_SINGLE_FULL_RTL_MEMORY_GATE',physical183_status=physical['status']);save()
 while True:
  m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
  if m.available>7500*1024*1024 and m.availpage>16000*1024*1024:break
  if time.monotonic()>deadline:raise TimeoutError('Single full RTL memory gate not ready')
  time.sleep(10)
 j.update(status='FULL_HLS_STARTED',available_mb=m.available//1024//1024,memory_gate='Single full RTL;7.5GiBphysical/16GiBcommit;noheavyVivadoalongside');save()
 env=os.environ.copy();env.update(TILE_PACKED_DETECTOR_HLS=str(W/'v170_hls67'),TILE_PACKED_DETECTOR_VECTORS=str(W/'v170_vectors08_wide'))
 for name in ['TILE_PACKED_SYNTH_ONLY','TILE_PACKED_SMALL_FIXTURE','TILE_PACKED_DETECTOR_SOURCE']:env.pop(name,None)
 with (W/'v170_hls67_console.log').open('w') as log:
  r=subprocess.run(['D:/2025.2/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(tcl)],env=env,stdout=log,stderr=subprocess.STDOUT)
 j.update(returncode=r.returncode,status='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD' if not r.returncode else 'FAILED_NO_PROMOTION');save()
 if r.returncode:raise RuntimeError('Full HLS67 RTL/IP failed')
except Exception as e:j.update(status='FAILED_NO_PROMOTION',error=str(e));save();raise
print(json.dumps(j),flush=True)
