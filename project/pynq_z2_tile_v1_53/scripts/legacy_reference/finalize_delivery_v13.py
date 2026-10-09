"""Build an evidence manifest, never infer hardware success from compilation."""
from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parents[1];W=R/'pynq_z2_tile_v1_5.sdk'
def read(p):return json.loads((R/p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
static=read('reports/board_acceptance/static_results.json')
queue=read('reports/board_acceptance/queue_capacity_counts.json')
held=read('reports/board_acceptance/queue_capacity_results.json')
soak=read('reports/board_acceptance/conveyor_observation.json')
boots=read('reports/board_acceptance/reboot_identity_checks.json')
assert len(boots)>=2 and len({b['hardware']['boot_id'] for b in boots})==len(boots) and all(b['passed'] for b in boots)
assert len(static)==6 and all(x['passed'] for x in static)
assert queue['passed'] and queue['event_delta']==16 and queue['dropped_delta']==4
assert len(held)==12 and all(x['passed'] for x in held)
baseline=read('reports/baseline_v12_hashes.json');changed=[]
for rel,h in baseline.items():
 p=R.parent/'pynq_z2_tile_v1_2'/rel
 if not p.exists() or digest(p)!=h:changed.append(rel)
assert not changed,changed
marker=read('reports/programmed_v13.json')
assert marker['active_application']=='hdmi_monitor'
for rel,h in marker['sha256'].items():assert digest(W/rel)==h
hardware=['system.bit','system.xsa','system.ltx','hdmi_monitor/build/hdmi_monitor.elf','hdmi_ethernet/build/hdmi_ethernet.elf']
sources=[]
for directory in ('rtl','constraints','sim','scripts','models'):
 sources.extend(p for p in (R/directory).rglob('*') if p.suffix in {'.v','.sv','.xdc','.py','.tcl','.c','.h','.ps1','.bat'})
sources.extend(p for p in (R/'host').glob('*') if p.suffix in {'.py','.html','.tcl','.ps1','.bat'})
for directory in ('app_sources','ethernet_sources'):
 sources.extend(p for p in (W/directory).rglob('*') if p.is_file())
sources.extend(p for p in W.glob('*') if p.suffix in {'.py','.bat','.tcl'})
sources.extend([R/'README.md',R/'启动检测工作站.bat'])
qtext='以 0.6 秒缺陷画面和 0.6 秒正常画面交替产生 16 次事件，空队列保留 12 张，额外 4 次明确计为队列满未留存。延迟取回 12 张证据，掩膜、两个框及面积全部与参考一致，ACK 错误为 0，最终队列清空。'
pressure='100 毫秒视频输入仍未稳定验收：曾有 16 次完整成功，也多次只有 9 次。对编码视频逐帧离线检查得到 16 次；同步读 FPGA 状态的诊断轮次也见到 16 次。播放器重开后差异仍出现，尚不能确定原因。最终报告保留失败轮次，不宣称 100 毫秒事件保证不漏。'
stext=(f"最终连续流水线视频观察约 {soak['duration_seconds']:.1f} 秒，板端帧号增长 {soak['frames_delta']}，完整采集增长 {soak['capture_delta']}，电脑收到 {soak['received_delta']} 张，保存 {soak['records_added']} 条；新增无效帧 {soak['invalid_delta']}、采集帧间隙 {soak['gap_delta']}、队列满丢失 {soak['dropped_delta']}。"+
 '较早调试会话曾出现 33 个采集帧间隙；最终软件会话在播放器关闭重开前后又累计 29 个间隙，具体原因未隔离。因此不能宣传全时段零丢帧，短时间观察也不能代替长时间可靠性验收。')
M=dict(version='Tile V1.3',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='USB_CORE_VALIDATED_WITH_OPEN_SHORT_VIDEO_ISSUE',
 conclusion='V1.3 已完成 FPGA 多区域框选、板端 12 槽事件缓存和电脑留图复核，核心功能通过开发板场景与容量验收，最终固件另通过跨两次重烧录留图验证。快速视频输入可靠性仍有未解决问题，以太网只完成编译与协议测试。',
 pressure_summary=qtext,pressure_caveat=pressure,soak_summary=stext,
 board='PYNQ-Z2 xc7z020clg400-1',tool_version='2025.2',video='1280x720 60Hz 74.25MHz',
 baseline_preserved=dict(version='V1.2',checked_files=len(baseline),changed_files=changed),
 hardware_sha256={p:digest(W/p) for p in hardware},programming=marker,
 sources_sha256={p.relative_to(R).as_posix():digest(p) for p in sorted(set(sources))},
 tests=dict(static_scenes_pass=6,static_mask_differences=0,queue_input='600ms static switches',queue_event_count=16,queue_retained=12,queue_explicit_full_drops=4,held_frames_exact=12,host_tests_pass=19,reprogramming_identity_checks=len(boots),
  video_100ms='INCONSISTENT_NOT_ACCEPTED',ethernet_build='PASS',ethernet_protocol_tests='PASS',ethernet_physical_test='NOT_RUN',real_tile_accuracy='NOT_EVALUATED',conveyor_observation=soak['passed']),
 timing=dict(wns_ns=.087,whs_ns=.050,internal_unconstrained_endpoints=0,legacy_cdc_critical_paths=5),
 resources=dict(lut=20555,registers=34371,bram36=57.5,dsp=2),
 evidence=['reports/board_static_final.log','reports/board_queue_capacity_final.log','reports/board_conveyor_observation.log','reports/board_pressure_final.log','reports/board_pressure_playerfix.log','reports/board_acceptance_prior/pressure_counts.json','reports/burst_hardware_trace.csv','reports/encoded_burst_reference.json','reports/host_tests_final.log','reports/timing_summary.rpt','reports/rebuild_boot_identity.log','reports/boot_identity_failure.log','reports/board_acceptance/reboot_identity_checks.json'],
 test_build_scope='Static/queue/conveyor tests used the identical final FPGA bitstream and image/queue algorithms. The last firmware change only replaced boot identity initialization; it was then tested across two actual programming cycles with saved normal and double-crack frames.',
 limitations=['Synthetic input, no real factory accuracy claim','Cell-connected grouping may merge nearby defects','Maximum eight regions, overflow indicated','Twelve retained frames only, volatile DDR','Continuous alarm is one event, not one product','USB takes about six seconds per full frame','HDMI boxes use previous frame','100ms video events have inconsistent repeatability','Legacy reset CDC warnings remain','Ethernet physical test pending'])
M['report_sha256']={p.relative_to(R).as_posix():digest(p) for p in (R/'docs').glob('*') if p.suffix in ('.docx','.md')}
qa=R/'reports/document_qa.json'
if qa.exists():M['document_qa']=json.loads(qa.read_text(encoding='utf-8'))
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=M['status'],baseline_files=len(baseline),source_files=len(M['sources_sha256']),soak=M['tests']['conveyor_observation']),ensure_ascii=False))
