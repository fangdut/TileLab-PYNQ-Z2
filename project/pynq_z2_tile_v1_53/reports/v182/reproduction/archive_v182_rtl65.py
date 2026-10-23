from pathlib import Path
import json,hashlib,shutil
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((W/'v182_hls65_full_pipeline.json').read_text());assert state['status']=='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD'
hls=W/'v170_hls65';out=P/'reports/v182/hls65_full_rtl';out.mkdir(parents=True,exist_ok=False)
for source,name in [(hls/'solution/sim/report/texture_integer_cosim.rpt','cosim.rpt'),(hls/'solution/syn/report/texture_integer_csynth.xml','csynth.xml'),(W/'v182_hls65_full_pipeline.json','pipeline.json')]:shutil.copy2(source,out/name)
export=hls/'solution/impl/ip/xilinx_com_hls_texture_integer_1_0.zip';proof=dict(scope='REDUCED_FULL_FUNCTION_RTL_AND_IP_EXPORT_NOT_PHYSICAL_OR_BOARD',passed=True,source_sha256=sha(hls/'src/texture_integer.cpp'),latency_cycles=[545278,545286],interval_cycles=545295,ip_export_sha256=sha(export),ip_export_bytes=export.stat().st_size,model_changed=False,threshold_changed=False,input_resolution_changed=False,board_programmed=False)
(out/'experiment.json').write_text(json.dumps(proof,indent=2)+'\n')
repro=P/'reports/v182/reproduction'
for name in ['prepare_v182_verified_collector.py','collect_v182_verified.py','archive_v182_rtl65.py']:shutil.copy2(W/name,repro/name)
p=R/'README.md';s=p.read_text(encoding='utf8');a='完整 RTL 仿真进行中，尚无新的整机时序与实板结果';assert a in s;s=s.replace(a,'两次完整功能缩小配置 RTL 通过（545,278 / 545,286 周期），IP 已导出；125 MHz 整机实现进行中，尚无新实板结果')
s=s.replace('最新已验证 V173 的源文件','此前已验证 V173 的源文件').replace('最新 V173 R2 的 [实板证据]','此前 V173 R2 的 [实板证据]');p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');a='Source-identical HLS65 fullRTL/IP is running, after which one guarded split125MHz physical trial may run.';assert a in s;s=s.replace(a,'Source-identical HLS65 two complete reduced-function RTL launches pass545278/545286cycles;IPexportSHA'+proof['ip_export_sha256']+'. One guarded split125MHz full physical trial is running; no new board result.')
p.write_text(s,encoding='utf8')
print(json.dumps(proof))
