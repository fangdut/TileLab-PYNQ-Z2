from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as ET
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((W/'v186_hls71_full_pipeline.json').read_text());assert state['status']=='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD'
out=P/'reports/v186/hls70_synthesis';out.mkdir(parents=True,exist_ok=False)
for a,b in [('v186_all_c01/summary.json','full_c_summary.json'),('v186_all_c01/results.json','full_c_results.json'),('v186_all_c01/complete_output_manifest.json','complete_output_manifest.json'),('v170_hls70/solution/syn/report/texture_integer_csynth.xml','csynth.xml'),('v186_cache_structure70.json','cache_structure.json'),('v186_cache_negative01/summary.json','cache_negative.json')]:shutil.copy2(W/a,out/b)
for n in ['line','normal_line']:shutil.copy2(W/'v170_hls70/solution/syn/verilog'/('texture_integer_'+n+'_RAM_2P_BRAM_1R1W.v'),out/('generated_'+n+'.v'))
out=P/'reports/v186/reopened_wrapper_failure';out.mkdir()
for a,b in [('v186_hls70_full_pipeline.json','pipeline.json'),('v186_continuation_failure_audit.json','audit.json'),('v186_hls70_continue_console.log','console.log'),('v186_synthesis_seal70.json','synthesis_seal.json')]:shutil.copy2(W/a,out/b)
out=P/'reports/v186/hls71_full_rtl';out.mkdir()
hls=W/'v170_hls71';source=hls/'src/texture_integer.cpp';assert sha(source)==sha(P/'experimental/texture_v170/hls/frozen/v170_hls70.cpp')==sha(P/'experimental/texture_v170/hls/frozen/v170_hls71.cpp')
for a,b in [(hls/'solution/sim/report/texture_integer_cosim.rpt','cosim.rpt'),(hls/'solution/syn/report/texture_integer_csynth.xml','csynth.xml'),(W/'v186_hls71_full_pipeline.json','pipeline.json')]:shutil.copy2(a,out/b)
import sys
sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
from check_normal_cache import inspect as cache
from check_mac_recurrence import inspect as recurrence
checks=dict(cache=cache(hls),recurrence=recurrence(hls));assert checks['cache']['passed'] and checks['recurrence']['all_banks_safe']
for n,j in checks.items():(out/(n+'.json')).write_text(json.dumps(j,indent=2)+'\n')
ip=hls/'solution/impl/ip/xilinx_com_hls_texture_integer_1_0.zip';x=ET.parse(out/'csynth.xml').getroot()
proof=dict(scope='REDUCED_FULL_FUNCTION_RTL_AND_IP_EXPORT_NOT_PHYSICAL_OR_BOARD',passed=True,source_sha256=sha(source),ip_export_sha256=sha(ip),ip_export_bytes=ip.stat().st_size,latency_cycles=[547158,547166],interval_cycles=547175,fixture_is_production_benchmark=False,resources={n.tag:int(n.text) for n in x.find('./AreaEstimates/Resources')},model_changed=False,threshold_changed=False,input_resolution_changed=False,board_programmed=False)
assert '547158' in (out/'cosim.rpt').read_text() and '547166' in (out/'cosim.rpt').read_text()
(out/'experiment.json').write_text(json.dumps(proof,indent=2)+'\n')
repro=P/'reports/v186/reproduction';repro.mkdir()
for n in ['prepare_v186_cache01.py','start_v186_cache_full_c.py','start_v186_hls70_synth.py','start_v186_continue_rtl70.py','start_v186_hls71_full.py','test_v186_cache_negative01.py','start_v186_physical01.py','collect_v186_verified.py','archive_v186_evidence01.py']:shutil.copy2(W/n,repro/n)
f=R/'README.md';s=f.read_text(encoding='utf8');a='C117 回归及 HLS70 综合进行中；效果尚未验证';assert a in s;s=s.replace(a,'117 张完整 C 输出字节一致；HLS71 两次完整功能缩小配置 RTL 通过（547,158 / 547,166 周期）；125 MHz 整机实现进行中，暂无新实板吞吐');f.write_text(s,encoding='utf8')
f=R/'FPGA_MIGRATION_STATUS.md';s=f.read_text(encoding='utf8');a='C117/HLS70synthesis running, no improvedFPS/timingclaim.';assert a in s;s=s.replace(a,'C117complete outputs byteidentical179. HLS70synth252BRAM18/213DSP/70467LUT/69970FF; dedicated24-bitcache and directconv-onlylinecontrols verified;6negativefixturesreject. Reopened-solution co-sim wrapper link failed beforeRTL;source/synthRTL unchanged. FreshHLS71 two complete reduced-function RTLcalls pass547158/547166cycles,interval547175,IPexportSHA'+proof['ip_export_sha256']+'. Guarded125MHzsplit fullphysicaltrial running; no improvedactualFPS/timingclaim.');f.write_text(s,encoding='utf8')
print(json.dumps(proof))
