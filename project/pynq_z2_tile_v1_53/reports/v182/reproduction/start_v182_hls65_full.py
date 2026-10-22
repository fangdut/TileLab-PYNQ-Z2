"""One fresh full RTL/IP run, gated by exact C and decoder/static proofs."""
from pathlib import Path
import ctypes,hashlib,json,os,subprocess,time,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
source=P/'experimental/texture_v170/hls/frozen/v170_hls64.cpp';frozen=source.with_name('v170_hls65.cpp');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not frozen.exists() and not (W/'v170_hls65').exists();frozen.write_bytes(source.read_bytes())
tcl=P/'experimental/control_decode_v182/build_full_hls.tcl';assert not tcl.exists();tcl.write_text(tcl.with_name('build_hls.tcl').read_text().replace('v170_hls64.cpp','v170_hls65.cpp'))
state=W/'v182_hls65_full_pipeline.json';j=dict(scope='SOURCE_BOUND_CONTROL_DECODE_FULL_RTL_NOT_BOARD',status='WAIT_C_SCALAR_STATIC_AND_RAM',source_sha256=sha(source),board_programmed=False)
def save():state.write_text(json.dumps(j,indent=2)+'\n')
class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','totalpage','availpage','totalvirtual','availvirtual','extended']]
try:
    save();deadline=time.monotonic()+2400;required=[W/'v182_all_c01/summary.json',W/'v182_decoder_checks01/summary.json',W/'v182_decode_structure_negative01/summary.json',W/'v182_recurrence64.json']
    while not all(p.exists() for p in required):
        if time.monotonic()>deadline:raise TimeoutError('Numerical/static evidence incomplete; no RTL launched')
        time.sleep(10)
    c=json.loads(required[0].read_text());assert c['cases']==c['correct']==117 and c['all_grid_values_exact'] and c['all_original_size_masks_exact']
    assert c['source_sha256']==sha(source)==sha(frozen)
    scalar=json.loads(required[1].read_text());assert scalar['passed'] and scalar['source_sha256']==sha(source)
    structure=json.loads(required[2].read_text());assert structure['passed'] and structure['positive']['source_sha256']==sha(source)
    recurrence=json.loads(required[3].read_text());assert recurrence['all_banks_safe'] and recurrence['source_sha256']==sha(source)
    assert json.loads((W/'v180_physical_pipeline01.json').read_text())['status']=='FAILED_NO_PROMOTION'
    while True:
        m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        if m.available>7500*1024*1024 and m.availpage>16000*1024*1024:break
        if time.monotonic()>deadline:raise TimeoutError('Single full RTL memory gate not ready')
        time.sleep(10)
    j.update(status='FULL_HLS_STARTED',available_mb=m.available//1024//1024,memory_gate='Single full RTL;7.5GiBphysical/16GiBcommit;noheavyVivadoalongside');save()
    env=os.environ.copy();env.update(TILE_PACKED_DETECTOR_HLS=str(W/'v170_hls65'),TILE_PACKED_DETECTOR_VECTORS=str(W/'v170_vectors08_wide'))
    for n in ['TILE_PACKED_SYNTH_ONLY','TILE_PACKED_SMALL_FIXTURE','TILE_PACKED_DETECTOR_SOURCE']:env.pop(n,None)
    with (W/'v170_hls65_console.log').open('w') as log:
        r=subprocess.run(['D:/2025.2/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(tcl)],env=env,stdout=log,stderr=subprocess.STDOUT)
    j.update(returncode=r.returncode,status='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD' if not r.returncode else 'FAILED_NO_PROMOTION');save()
    if r.returncode:raise RuntimeError('Full HLS65 RTL/IP failed')
except Exception as e:j.update(status='FAILED_NO_PROMOTION',error=str(e));save();raise
print(json.dumps(j),flush=True)
