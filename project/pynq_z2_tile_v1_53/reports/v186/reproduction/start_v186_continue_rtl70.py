"""Reuse sealed synthesis only after exact C regression and RAM/source guards."""
from pathlib import Path
import ctypes,hashlib,json,os,subprocess,time,sys,xml.etree.ElementTree as ET
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020');hls=W/'v170_hls70';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=W/'v186_hls70_full_pipeline.json';assert not state.exists();j=dict(scope='SEALED_EXISTING_SYNTHESIS_FULL_RTL_NOT_BOARD',status='WAITING_C_AND_RAM',board_programmed=False)
def save():state.write_text(json.dumps(j,indent=2)+'\n')
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','totalpage','availpage','totalvirtual','availvirtual','extended']]
try:
 save();deadline=time.monotonic()+3600
 while not (W/'v186_all_c01/summary.json').exists():
  if 'Traceback (most recent call last)' in (W/'v186_cache_full_c.log').read_text(errors='replace'):raise RuntimeError('C regression failed; no RTL')
  if time.monotonic()>deadline:raise TimeoutError('C regression not ready')
  time.sleep(10)
 c=json.loads((W/'v186_all_c01/summary.json').read_text());source=hls/'src/texture_integer.cpp'
 assert c['cases']==c['correct']==117 and c['all_grid_values_exact'] and c['all_original_size_masks_exact']
 assert c['source_sha256']==sha(source)==sha(P/'experimental/texture_v170/hls/frozen/v170_hls70.cpp')
 complete=list((W/'v186_all_c01').glob('*/result.bin'));assert len(complete)==117
 for f in complete:assert f.read_bytes()==(W/'v179_all_c05'/f.parent.name/'result.bin').read_bytes()
 assert json.loads((W/'v186_cache_negative01/summary.json').read_text())['passed']
 assert json.loads((W/'v185_physical_pipeline01.json').read_text())['status']=='FAILED_NO_PROMOTION'
 assert 'PACKED_FULL_DETECTOR_SYNTHESIS_ONLY_RTL_AND_BOARD_PENDING' in (W/'v170_hls70_console.log').read_text(errors='replace')
 assert not (hls/'solution/sim/report/texture_integer_cosim.rpt').exists()
 sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
 from check_normal_cache import inspect as cache_inspect
 from check_mac_recurrence import inspect as recurrence_inspect
 checks=dict(cache=cache_inspect(hls),recurrence=recurrence_inspect(hls));assert checks['cache']['passed'] and checks['recurrence']['all_banks_safe']
 report=hls/'solution/syn/report/texture_integer_csynth.xml';r=ET.parse(report).getroot()
 assert int(r.findtext('./AreaEstimates/Resources/DSP'))<=220 and int(r.findtext('./AreaEstimates/Resources/BRAM_18K'))<=276
 rtl=lambda:{f.name:sha(f) for f in (hls/'solution/syn/verilog').glob('*.v')}
 seal=dict(scope='EXACT_SYNTHESIZED_SOURCE_AND_RTL_SEAL_BEFORE_CONTINUATION',source_sha256=sha(source),csynth_sha256=sha(report),rtl_sha256=rtl(),checks=checks)
 assert seal['rtl_sha256'];(W/'v186_synthesis_seal70.json').write_text(json.dumps(seal,indent=2)+'\n')
 while True:
  m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
  if m.available>7500*1024*1024 and m.availpage>16000*1024*1024:break
  if time.monotonic()>deadline:raise TimeoutError('Single full RTL memory gate not ready')
  time.sleep(10)
 j.update(status='FULL_RTL_STARTED_FROM_SEALED_SYNTHESIS',source_sha256=sha(source),available_mb=m.available//1024//1024,synthesis_seal_sha256=sha(W/'v186_synthesis_seal70.json'));save()
 env=os.environ.copy();env['TILE_PACKED_DETECTOR_HLS']=str(hls)
 with (W/'v186_hls70_continue_console.log').open('w') as log:
  result=subprocess.run(['D:/2025.2/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(P/'experimental/cache_split_v186/continue_rtl.tcl')],env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError('Full RTL/IP continuation failed')
 assert sha(source)==seal['source_sha256'] and sha(report)==seal['csynth_sha256'] and rtl()==seal['rtl_sha256'],'Synthesis changed during continuation'
 j.update(status='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD',synthesized_source_and_rtl_unchanged=True,returncode=0);save()
except Exception as e:j.update(status='FAILED_NO_PROMOTION',error=repr(e));save();raise
print(json.dumps(j),flush=True)
