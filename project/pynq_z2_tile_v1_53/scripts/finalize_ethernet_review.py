from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).resolve().parents[1];T=R/'reports/ethernet_20260926'
def read(n):return json.loads((T/n).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=read('baseline.json');final=read('scheduled.json');recovery=read('recovery.json')
static=read('board_scheduled/static_results.json');queue=read('board_scheduled/queue_capacity_counts.json')
soak=read('board/conveyor_observation.json');steady=read('board_steady/conveyor_observation.json')
scheduled=read('board_scheduled/conveyor_observation.json')
old=json.loads((R/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
unchanged={k:digest(R/k)==v for k,v in old['sources_sha256'].items() if k.startswith(('rtl/','constraints/'))}
assert all(unchanged.values())
ws=R/'pynq_z2_tile_v1_5.sdk';programmed=json.loads((R/'reports/programmed_v13.json').read_text())
assert programmed['active_application']=='hdmi_ethernet'
assert all(digest(ws/k)==v for k,v in programmed['sha256'].items())
assert final['frames'][-1]['boot_id']==programmed['boot_id']
files=[*R.glob('host/*.py'),R/'host/workstation.html',R/'host/start_station.ps1',R/'README.md',R/'启动以太网工作站.bat',
 *ws.glob('ethernet_sources/*'),ws/'program_ethernet.tcl',ws/'program_ethernet.bat',ws/'build_ethernet.py',ws/'rebuild_ethernet.py',
 R/'scripts/prepare_ethernet.py',R/'scripts/benchmark_ethernet.py',R/'scripts/check_ethernet_recovery.py',R/'scripts/board_v13_acceptance.py',R/'scripts/board_soak.py',R/'scripts/build_ethernet_report.py',R/'scripts/finalize_ethernet_review.py',
 R/'docs/Tile_V1.3_以太网实测与项目改进评审报告.docx']
proof=dict(revision='Tile V1.3 Ethernet review 2026-09-26',generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 conclusion='以太网传输速度和内容完整性验收通过；真实网线场景与恢复测试通过。移动视频仍出现过偶发采集帧间隙，严格连续采集尚未全面闭环。',
 baseline=base['summary'],final=final['summary'],speedup=final['summary']['goodput_MB_s']['median']/base['summary']['goodput_MB_s']['median'],
 final_benchmark=dict(frames=len(final['frames']),measured=300,board_deltas=final['board_deltas'],passed=final['passed']),
 static_scene_passes=sum(s['passed'] for s in static),queue_capacity=queue,recovery=recovery,
 conveyor_startup={k:v for k,v in soak.items() if k!='samples'},conveyor_steady={k:v for k,v in steady.items() if k!='samples'},conveyor_final={k:v for k,v in scheduled.items() if k!='samples'},
 host_tests=dict(count=22,passed='Ran 22 tests' in (T/'host_tests.log').read_text() and '\nOK' in (T/'host_tests.log').read_text()),
 unmodified_rtl_constraints=unchanged,programmed=programmed,
 backup=dict(path='D:/Vivado/_baseline_backups/tile_v13_before_ethernet_20260926.zip',sha256='47d57d008b039e9d6f5768b2fb11d6b4c45771a964e4fac853d01ce79c990424',bytes=215743085),
 limitations=['合成素材，未验证真实工厂准确率','历史 100ms 短事件结果不稳定，本轮未重新验收','移动测试有偶发采集间隙，不能保证每一帧均留存','最终长视频有两次电脑接收计数至少14.12秒和16.20秒不增加，随后恢复，根因未定位','12 槽 DDR 易失；超过容量显式计数丢失','连续坏品没有独立产品编号','网格可能合框；最多 8 区域','HDMI 叠框使用上一帧；保存证据同帧','5 个 CDC 不安全端点待专项审核','本轮测试 TCP 断连，未完成物理拔网线和断电恢复测试','DHCP 路由器模式未实测'],
 sources_sha256={str(p.relative_to(R)).replace('\\','/'):digest(p) for p in files if p.is_file()},
 evidence_sha256={str(p.relative_to(R)).replace('\\','/'):digest(p) for p in T.rglob('*.json') if 'doc_qa' not in p.parts})
(R/'ETHERNET_REVIEW_MANIFEST.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(speedup=proof['speedup'],unchanged_hdl=len(unchanged),programmed_boot=programmed['boot_id'],tests=proof['host_tests']),ensure_ascii=False))
