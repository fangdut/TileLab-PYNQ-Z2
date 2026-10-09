from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_22'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
fw=read(O/'firmware_audit.json');sync=read(O/'stimulus_board/summary.json');old=read(O/'old_state_lock_counterexample.json')
w=read(O/'admission_board/summary.json');n=read(O/'dma_recovery_native.json');h=read(O/'health_native.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json');ui=read(O/'ui_restart_after.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');plan=read(R/'ITERATION_PLAN.json')
assert all(x['passed'] for x in (fw,sync,w,n,h,t,f,r,ui,c,a,b)) and old['baseline_reproduced']
assert read(O/'descriptor_native.json')['passed'] and read(O/'firmware_crc_test.json')['passed'] and read(O/'native_sg/result.json')['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 179 tests' in units and units.rstrip().endswith('OK')
baseline=read(B/'DELIVERY_MANIFEST.json');assert baseline['status']=='BOARD_VALIDATED_CAPTURE_ADMISSION_WITH_KNOWN_LIMITS'
summary=dict(version='V1.23',passed=True,firmware=fw,stimulus_board=sync,old_counterexample=old,admission_board=w,recovery_native=n,health_native=h,unit_tests=179,
 transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,
 baseline_manifest_sha256=hashlib.sha256((B/'DELIVERY_MANIFEST.json').read_bytes()).hexdigest(),
 inherited_recovery_evidence=dict(version='V1.21',manifest=str(R.parent/'pynq_z2_tile_v1_21/DELIVERY_MANIFEST.json'),scope='Prior physical DMA recovery/generation campaign, inherited; fresh actual-C regression and strict firmware behavior audit in this release'))
(O/'stimulus_sync_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
transport='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
doc=f'''# Tile V1.23 输入播放器状态可靠性与实板报告

## 解决的问题

V1.22 中，HDMI 命令文件被 Windows 短暂独占时，正式状态 HTTP 请求会异常断开。实际反例已保留，释放锁后恢复，采集并未停下。另一个显示问题是界面把已写入的输入命令当成输入状态，没有单独显示播放器是否收到、是否仍然新鲜。

V1.23 将输入请求与播放器报告分开。读取命令文件失败，状态接口正常返回并标明不可读；播放器文件被占用、格式损坏、太大、时间过期或报告错误，也都显示明确状态。旧报告不再被当作当前确认。

这项修复不在 PC 上运行裂纹识别。FPGA 做候选、掩码、区域、产品和最佳帧判定；ARM 管理 DMA、帧槽、事件、压缩和传输；电脑处理接收、存档、复核和输入播放器的可观测状态。

## 工程与回退

工程 D:/Vivado/pynq_z2_tile_v1_53；Vivado 同名 .xpr；Vitis workspace 同名 .sdk。V1.22 原工程保留，备份 {plan['backup']}，SHA256 {plan['backup_sha256']}。

Vivado 工程正常生成，BIT/XSA/LTX 沿用 V1.15。Vitis 完整构建，ELF SHA256 {fw['elf_sha256']}。逐文件审计确认固件只更新版本常量、注释和显示文字；DMA、恢复、队列、ACK 和检测规则未变。保留浮点中断上下文、4 KiB IRQ 栈与整数 memcpy。本版不宣称新增时序收敛、频率或算法准确率。

## 状态规则和同步原理

命令文件描述“想播放什么”，播放器遥测描述“刚才正在播放什么”。读取同一个打开文件句柄的数据和修改时间，避免名称被原子替换后，旧内容配上新文件时间。命令最多 128 字节、遥测最多 16 KiB，异常文件不会拖垮状态接口。

只有输入名称相同、播放器报告时间不早于该命令的写入时间、报告不超过 1.5 秒、没有错误、且阶段不是加载或预热，才显示已确认。未来超过 0.5 秒的时钟也不确认。使用有时区 UTC；这不是严格的分布式时钟协议，系统时间跳变仍可能让确认暂时退回未知。

| 状态 | 意义 |
|---|---|
| COMMAND_UNAVAILABLE | 命令缺失、被占用、编码或内容异常；保留上次请求但不确认 |
| PLAYER_UNAVAILABLE / PLAYER_INVALID | 播放器遥测不可读或格式不可信 |
| SWITCHING | 命令已保存，等待对应的新报告或加载结束 |
| STALE / CLOCK_UNCERTAIN | 报告过期或时间异常，不确认当前输入 |
| PLAYER_ERROR | 播放器自己报告错误 |
| READY | 播放器报告与输入请求匹配且新鲜 |

READY 只说明本机播放器自报状态，不证明 HDMI 线、显示器或 FPGA 已收到该画面。板端采集健康另行显示；也不能把渲染回调次数解释成摄像头曝光次数或物理 HDMI 帧数。

## 本版实际验证

179 项独立主机测试通过，新加 19 项覆盖有效/无效标识、过期与未来时间、同源旧报告、加载和预热、文件缺失、超长和坏编码、错误字段以及正式 HTTP 接口在真实 Windows 独占文件锁下的响应。

实际 WPF 播放器、正式工作站、HDMI 输入与 PYNQ-Z2 同时运行，进行了三组有界故障：

1. 命令文件独占锁：状态接口返回 COMMAND_UNAVAILABLE，连续采集与渲染继续；释放后恢复 READY。
2. 遥测文件允许读、禁止替换：保留真实旧报告，再请求空传送带。界面先 SWITCHING，再因超过 1.5 秒变为 STALE；开发板采集保持正常；释放后播放器新报告确认 station_6。
3. 遥测文件独占锁：界面 PLAYER_UNAVAILABLE，HTTP 不断开，释放后恢复。最后恢复真实照片连续运动。

没有伪造板端图像或 JSON 遥测；第二项通过 Windows 共享模式阻止原子替换，保留的是真实旧报告。所有窗口无新增采集 gaps、invalid、dropped、ACK、描述 CRC 错误，也没有新增存档。UI 截图分别记录命令不可读和遥测过期，证明页面未把这些状态显示成已确认。

实际 C 回归再次运行 20 个恢复/代次场景、健康边界和随机检查、3000 组 CRC/1280 单比特拒绝及 48 槽所有权。V1.21 物理 DMA 三次恢复与代次证据作为继承依据；本版未重复整套 DMA 停止试验。

## 完整回归结果

停止取图的 4 项实板受控调度、50 对同事件 RAW/RLE 逐字节比较、9 类网络故障、3 类主机退出/JTAG 重新下载、正式 UI 待确认恢复通过。恢复确认零新取图，原截图哈希不变。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体减少 % |
|---|---:|---:|---:|
{transport}

连续运动 {c['seconds']:.3f} 秒，接收 {c['host_captures']} 张图，10 件预期缺陷产品均留图；独立核对掩码、区域框、面积和来源身份，最大居中偏差 {a['max_center_error_px']} 像素。后台冻结预览仍保存 10 件事件，应用层接收字节率减少 {b['received_rate_reduction_percent']:.3f}%。请求耗时不等于纯线速，冻结测试也不说明电脑可显示 60 fps。

## 操作与下一步

接线仍为电脑 HDMI → 板 IN → 板 OUT → 显示器；USB PROG UART 与直连网线保持；720p60 输入。下载本版 .sdk/program_ethernet.bat，再用本版“启动以太网工作站.bat”。在“HDMI 测试输入”下方核对请求、播放器报告、年龄和状态；结合板端采集健康判断问题位于哪里。

最终恢复真实照片匀速运动、仅预览及 1 GiB 存档上限，测试只保留有界证据。各版源文件哈希、下载文件及实测详情见 DELIVERY_MANIFEST.json。

下一步仍需研究跨材质弱裂纹与无强种子裂纹的漏检、材料独立盲测、真实相机曝光/运动模糊、高速居中偏差、HDMI 前一帧框、既有 CDC、中断最坏栈和物理 HDMI 失锁恢复。文件时效确认不是物理显示确认；长时间停止接收和掉电也不能保住尚在有限 DDR 队列中的证据。CRC 检测意外损坏，不提供安全认证。PNG 和 SQLite 仍非跨文件原子事务。
'''
(R/'docs/Tile_V1.23_输入状态同步与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# Tile V1.23

修复 HDMI 命令文件共享冲突导致状态接口断开；分别显示输入请求、播放器报告与时效。

Vivado：pynq_z2_tile_v1_53.xpr；Vitis workspace：pynq_z2_tile_v1_53.sdk。
完整报告：docs/Tile_V1.23_输入状态同步与实板报告.md。
下载 .sdk/program_ethernet.bat，再从本版启动工作站；V1.22 原工程及 ZIP 保留。
FPGA 检测和 ARM 通道行为沿用基线，配套固件只更新版本标识。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.23 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:28px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.23 / 输入状态同步</p><h1>输入请求与播放器报告分别确认</h1><section><strong>3 组实际文件冲突通过</strong><p>命令被占用时状态接口继续响应；播放器旧报告显示切换中或过期，文件恢复后重新确认。采集持续、零新增错误、零新增存档。</p></section><section><h2>179 项主机测试通过</h2><p>4 项取图停止实板测试、50 对实际图、9 类网络故障、3 类重启、UI 确认与连续产品回归通过。最大居中偏差 {a['max_center_error_px']} 像素，后台字节率减少 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>验证边界</h2><p>播放器报告不证明物理 HDMI 链路。看板端健康确认实际采集；真实照片合成运动仍不能证明工厂识别精度。固件仅版本变化。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.23 report generated from fresh passing evidence')
