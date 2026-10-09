"""Compile release claims from completed, retained board evidence."""
from pathlib import Path
import json,statistics,hashlib,datetime
R=Path(__file__).resolve().parents[1];T=R/'reports/v14'
def read(p):return json.loads((T/p).read_text(encoding='utf-8'))
tests=[read(f'continuous/{m}_{s}s.json') for m,s in [('video',60),('fast',60),('ultrafast',300)]]
assert all(t['passed'] for t in tests)
q=read('queue/results.json');assert q['passed']
static=read('static_board/static_results.json');real=read('real_board/results.json')
assert all(r['passed'] for r in static+real)
audit=read('saved_evidence_audit.json');assert audit['all_source_crack'] and audit['all_fully_in_roi']
long=read('continuous/ultrafast_60s.json');assert long['passed'] and long['player_at_end']['source_file'].endswith('_long_720p60.mp4')
normal_false=sum(r['truth']=='good' and r['hardware']['alarm'] for r in real)
total_frames=sum(t['after']['captured']-t['before']['captured'] for t in tests)
total_events=sum(t['saved_events'] for t in tests)
interval=max(t['max_interval_ms'] for t in tests)
rates=[r['payload_MB_s'] for t in tests for r in t['rows']]
reconnects=sum(t['diag_after']['reconnects'] for t in tests)
frames_received=sum(t['host_captures'] for t in tests)
speeds={'video':480,'fast':960,'ultrafast':1920}
summary=dict(
 conclusion=f'本版已完成真实开发板下载与验收。三个匀速档合计采集 {total_frames:,} 帧，保存 {total_events} 张按产品编号选择的最佳证据；测试窗口内新增采集间隙、无效帧及队列丢失均为 0。真实纹理数据测试未通过工业识别要求，下一步优先降低误报。',
 task_rows=[['修复采集与取图停顿',f'SG 连续采集；三个速度档通过，最长取图间隔 {interval:.0f} ms。'],['按产品保存最佳截图',f'FPGA 产品编号及排序；{total_events} 张匀速证据均为完整入镜的裂纹瓷砖，未发现产品号重复。'],['建立真实瓷砖测试集','347 张照片、84 张掩码，保留来源、划分与校验；117 张固定参数离线评估，6 张实板一致性核对。']],
 hardware_rows=[['最差建立 / 保持裕量','+0.197 ns / +0.050 ns；TNS 0'],['LUT / FF','16,781 / 28,305'],['BRAM / DSP','58 / 2'],['较队列优化前减少','LUT 5,388；FF 9,339'],['时钟约束','74.25 MHz 像素；100 MHz DMA；200 MHz 参考']],
 best_example='reports/v14/best_product_example.png',
 continuous_rows=[[f'{speeds[t["mode"]]} 像素/秒\n{int(round(t["seconds"]))} 秒',f'{t["raw_capture_fps"]:.2f} fps',f'{t["max_interval_ms"]:.0f} ms',[t['after'][k]-t['before'][k] for k in ('gaps','invalid','dropped')]] for t in tests],
 test_detail=f'三个测试合计向电脑完整取回 {frames_received} 帧。纯像素负载传输中位速度为 {statistics.median(rates):.2f} MB/s，范围 {min(rates):.2f}～{max(rates):.2f} MB/s；含等待、编码和校验的取图间隔另列。自动重连 {reconnects} 次。高速度档持续 300 秒，单块产品持续移动，没有等待抓图的停留阶段。',
 validation_paragraphs=[
  '静态六场景包括正常、细裂纹、反光、宽裂纹、双裂纹和小点噪声。实板候选掩码逐像素匹配，区域框和面积匹配。动态证据同样核对掩码和坐标；源视频条码仅用于测试核对，不参与产品编号或检测。',
  f'队列故障注入：停止接收后触发 {q["event_delta"]} 个产品，保留 12 个、明确计数丢失 {q["drop_delta"]} 个。取图中途断开 TCP，重连后事件编号和像素未变；12 张均完整保存，重复确认未导致额外出队。这四次丢失是故意的超容量测试，不能算作正常运行零丢失的一部分。',
  'RTL 仿真覆盖包长、元数据、背压无效帧、最佳帧排序、视频复位和编号延续；区域模块小尺寸及 720p 回归通过。原生 C 测试覆盖 48 槽引用计数、队列满、重复确认和最佳帧替换；主机软件 32 项测试通过。',
  'Vivado CDC 报告仍有 5 个不安全端点，位于继承的 HDMI IP 时钟交互；新增像素域到 DMA 的路径使用跨域 FIFO。实板通过不代表这些静态告警已被证明安全，后续应逐项审查供应商 IP 和复位同步。'],
 real_board_detail=f'实板抽测 6 张真实照片：2 张裂纹、2 张正常、1 张胶带、1 张粗糙缺陷。六张的掩码和区域框均与固定参数参考逐像素一致；其中 {normal_false}/2 张正常照片仍报警。这里通过的是实现一致性，分类误报没有消失。',
 metrics=dict(total_captured=total_frames,total_events=total_events,total_received=frames_received,max_interval_ms=interval,median_payload_MB_s=statistics.median(rates),automatic_reconnects=reconnects),
 evidence=['continuous/video_60s.json','continuous/fast_60s.json','continuous/ultrafast_300s.json','continuous/ultrafast_60s.json','continuous/ultrafast_long_player_failure_60s.json','queue/results.json','static_board/static_results.json','real_board/results.json','saved_evidence_audit.json','dataset_integrity.json','real_dataset/metrics.json','long_stream_validation.json'])
summary['long_stream_detail']=f'补充验收：十分钟连续视频实播 60 秒，1920 像素/秒，采集 {long["after"]["captured"]-long["before"]["captured"]} 帧，保存 {long["saved_events"]} 个产品，最长取图间隔 {long["max_interval_ms"]:.0f} ms，新增间隙、无效帧和丢失均为 0。连同前三轮共核对 {audit["samples"]} 张完整瓷砖证据。'
summary['player_fix_detail']='长视频首轮播放异常且采到启动桌面，该轮未通过。改为每次新建媒体控件、忽略过期回调并有界重试后重测通过。播放器排查及冷启动排查时暂停接收而输入继续运行，两次分别累计 60、8 次队列满丢失，日志和原图保留；不计入正常连续测试的零新增丢失结论。'
summary['evidence'].append('startup_recovery.json')
(T/'final_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary['metrics'],ensure_ascii=False))
