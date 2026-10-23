from pathlib import Path
import json,hashlib,shutil,re,sys
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((W/'v185_hls69_full_pipeline.json').read_text());assert state['status']=='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD'
hls=W/'v170_hls69';assert sha(hls/'src/texture_integer.cpp')==sha(P/'experimental/texture_v170/hls/frozen/v170_hls69.cpp')==sha(P/'experimental/quarter_pipeline_v185/texture_quarter_pipeline.cpp')
out=P/'reports/v185/hls69_full_rtl';out.mkdir(parents=True,exist_ok=False)
for a,b in [(hls/'solution/sim/report/texture_integer_cosim.rpt','cosim.rpt'),(hls/'solution/syn/report/texture_integer_csynth.xml','csynth.xml'),(W/'v185_hls69_full_pipeline.json','pipeline.json')]:shutil.copy2(a,out/b)
line=next(l for l in (out/'cosim.rpt').read_text().splitlines() if re.search(r'Verilog\s*\|\s*Pass',l));values=[x.strip() for x in line.strip('|').split('|')];assert values[:2]==['Verilog','Pass'];latency=[int(values[2]),int(values[4])];interval=int(values[5]);assert latency==[547158,547166] and interval==547175
sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
from check_row_address import inspect as row_inspect
from check_quarter_pipeline import inspect as quarter_inspect
from check_operation_decode import inspect as decode_inspect
from check_mac_recurrence import inspect as recurrence_inspect
checks=dict(row=row_inspect(hls),quarter=quarter_inspect(hls),decoder=decode_inspect(hls),recurrence=recurrence_inspect(hls));assert checks['recurrence']['all_banks_safe']
for name,value in checks.items():(out/(name+'_structure.json')).write_text(json.dumps(value,indent=2)+'\n')
ip=hls/'solution/impl/ip/xilinx_com_hls_texture_integer_1_0.zip';proof=dict(scope='REDUCED_FULL_FUNCTION_RTL_AND_IP_EXPORT_NOT_PHYSICAL_OR_BOARD',passed=True,source_sha256=sha(hls/'src/texture_integer.cpp'),latency_cycles=latency,interval_cycles=interval,fixture_is_production_benchmark=False,ip_export_sha256=sha(ip),ip_export_bytes=ip.stat().st_size,model_changed=False,threshold_changed=False,input_resolution_changed=False,board_programmed=False)
(out/'experiment.json').write_text(json.dumps(proof,indent=2)+'\n');shutil.copy2(W/'archive_v185_rtl69.py',P/'reports/v185/reproduction/archive_v185_rtl69.py')
p=R/'README.md';s=p.read_text(encoding='utf8');a='HLS69 完整检测器 RTL 正在验证，尚无新实板吞吐';assert a in s;s=s.replace(a,'HLS69 两次完整功能缩小配置 RTL 通过（547,158 / 547,166 周期），IP 已导出；125 MHz 整机实现进行中，尚无新实板吞吐');p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');a='Source-identical HLS69 fullRTL/IP is running after failed183; one guarded fresh125MHzsplit physical trial waits for fullRTL.';assert a in s;s=s.replace(a,'Source-identical HLS69 fullRTL passes two complete reduced-function calls547158/547166cycles,interval547175;IPexportSHA'+proof['ip_export_sha256']+'. This is not productionFPS. One guarded fresh125MHzsplit physical trial is running after failed183.');p.write_text(s,encoding='utf8')
print(json.dumps(proof))
