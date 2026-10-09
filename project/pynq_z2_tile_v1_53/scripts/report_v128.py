from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_27'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=dict(firmware='firmware_audit.json',parser='native_stimulus/summary.json',stimulus='stimulus_board/summary.json',render='render_board/summary.json',station='station_continuous.json',identity='station_identity_audit.json',readiness='boot_readiness.json')
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
log=(O/'host_tests.log').read_text();assert 'Ran 228 tests' in log and log.rstrip().endswith('OK')
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');r=s['render'];c=s['station'];identity=s['identity']
summary=dict(version='V1.28',passed=True,unit_tests=228,**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),
    inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Unchanged PL detector; no new accuracy claim'),
    test_scope='Fresh host/native tests, nine real input-identity cases, actual bounded WPF hold observed in HDMI frame codes, and continuous best-evidence acceptance. Unchanged complete network fault suite not rerun.',limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
doc=f'''# Tile V1.28 运动源绘制进度与 HDMI 实板报告

## 做成了什么

V1.28 在工作台分开显示三件事：当前播放器是否采用本次输入请求、本机运动源是否有实际绘制进展、开发板是否收到完整 HDMI 帧。这样即使播放器仍在发状态、HDMI 仍有 60 Hz 的完整帧，素材本身卡住时也能给出提示。

FPGA 仍负责 720p60 裂纹候选检测、四级弱响应支持、区域框、产品跟踪、最佳帧选择和 CRC。ARM/Vitis 仍负责 DMA、帧槽、事件确认、有界恢复与无损传输。电脑增加的是输入源可观测性，视觉算法没有转移到电脑。PL 与固件业务逻辑保持前版；Vitis 仅更新身份为 0x11c00 并完整重建。

## 先区分“时间在走”和“画面在走”

原有 RenderedFrames 在动画回调中递增，PositionSeconds 来自计时器。它们不能单独说明 WPF 已执行图像绘制。本版在真实 OnRender 绘制回调完成后记录 DrawnFrames 和 DrawnSourceFrame；前者表示绘制次数，后者表示所绘制内容的源帧码。

主机只有在绘制次数增加、同时所绘制帧码变化时才承认运动有进展。用公式表示：`draw_count_new > draw_count_old` 且 `source_frame_new != source_frame_old`。帧码会循环，从周期末回到零仍是有效进展；同一静止内容因窗口刷新而被重画，不能冒充运动。

超过 1 秒未观察到这种变化，且播放器状态仍新鲜，显示 STALLED。时间间隔使用电脑单调时钟，不依赖墙上时钟的校准。若主机超过 1.5 秒没有观察，重新建立观察基线，不把没人观察的那段时间当成已证实的卡顿。计数复位、新播放器或新素材也需要重新观察；只换同一素材的请求编号不会重置卡顿计时。

静态图片显示 NOT_REQUIRED，不要求它运动。使用 MediaElement 的媒体源暂没有同等逐帧绘制证据，显示 UNOBSERVED，不能用播放计时器代替验证。输入身份未确认时不判断绘制进展。现有 ready/identity_confirmed 仍表示请求采用确认，motion 字段单独说明画面进度，两者可以出现“请求已采用、画面卡住”。

这里的绘制是本机 WPF 层面的事实，不是显示器扫描输出的硬件测量。物理链路仍需看板端采集和真实图像。本版在测试中实际解读 FPGA 采回画面上的源帧码来交叉验证，没有只相信播放器自己的报告。

## 一步一步测试及结果

1. 228 项主机测试通过，其中新增 20 项进度状态测试、2 项身份/进度独立性集成测试。覆盖静态源、媒体源、时间/观察间隙、计数复位、帧码回绕、同帧重画、同名重选、卡顿边界与恢复。
2. 实际 C# 命令解析器 736 组检查通过，真实 WPF 渲染器编译通过。有界诊断冻结拒绝 6 类越界/非有限参数；正常启动冻结长度为零。
3. 重新建立 Vivado 工程，完整构建 Vitis 平台、BSP、ELF；反汇编核对中断浮点上下文、4096 字节 IRQ 栈、整数 memcpy。旧版源码和 BIT/XSA/LTX 的哈希均核对。继承的时序报告不是本版重新综合实现的结果。
4. V1.27 的九类真实输入身份专项在本版重新通过：同名新请求、命令/状态/启动标记共享冲突、坏编码、超长命令、旧格式、真实播放器重启。采集继续，状态接口不崩溃。
5. 使用正常生产播放器代码中的有界诊断参数，仅冻结动画 8 秒；状态定时器、工作台和真实开发板继续运行。首次观测冻结到识别卡顿相差 **{r['stall_detection_delay_seconds']:.3f} 秒**。冻结期间开发板继续收到 **{r['complete_frames_during_hold']} 个**完整帧。
6. 冻结阶段取得 **{len(r['held'])} 个**真实 HDMI 抽样，源帧码相同，PNG SHA256 相同，FPGA 像素 CRC 相同；播放器 UTC 仍更新。重复选择同名视频产生新的请求编号，但没有掩盖卡顿。动画恢复后，真实 HDMI 源帧码重新前进，软件进度也恢复 PROGRESSING。
7. 诊断结束后重启无诊断参数的正常播放器。静态图片连续观察 2.2 秒保持静态豁免，没有误报卡顿；随后恢复真实照片匀速回放。专项测试未增加归档，未新增采集间隙、坏帧、队列丢失或 ACK/描述 CRC 错误。
8. 正常播放器连续运动 **{c['seconds']:.3f} 秒**，主机抽样 **{c['host_captures']} 张**，保存 **{c['saved']} 个**缺陷产品各一张最佳图，最大居中偏差 **{identity['max_center_error_px']} 像素**。保存图掩码、框、区域面积与参考模型相符，CRC 通过，未发生重复产品证据或已观测缺陷产品遗漏。

本轮最大居中偏差 {identity['max_center_error_px']} 像素，上一版 V1.27 为 10 像素，两次在不同时间运行。仍满足既定 32 像素目标，但不能据此声称位置精度改善，也不能把差值全部归因于这次改动。高速源调度、绘制抖动与最佳帧选择仍有优化空间；未用重复测试挑选更漂亮的数字。

测试冻结的是本机源动画，没有拔 HDMI、网线或开发板电源。这里的恢复是动画恢复，不冒称验证了物理 HDMI 失锁恢复。没有重新运行全部旧版网络故障注入，也没有新的检测准确率或网络提速结论。

## 工程与回退

工程 `{R.as_posix()}`；Vivado 文件 `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`。固件 SHA256 `{s['firmware']['elf_sha256']}`。旧版原工程 `{B.as_posix()}` 保留；轻量备份 `{plan['backup']}`，SHA256 `{plan['backup_sha256']}`。备份保留源码、文档和关键下载产物，全部素材及历史测试数据仍在原工程。

连接保持电脑 HDMI → 板上 IN → OUT → 显示器，USB 接 PROG UART，网线直连电脑，1280×720 60 Hz。停止旧工作台后通过本版 `.sdk/program_ethernet.bat` 下载，再启动 `host/start_station.ps1`。正常启动不带诊断冻结参数。默认仅预览；自动存档上限 1 GiB，有界测试结束后恢复仅预览，避免一直积累截图。

## 局限与后续方向

识别方面仍受材质、裂纹宽度、低对比度和光照影响。V1.24 开发集结果不能当作新的盲测；跨材质误报和真实相机曝光/运动模糊仍未解决。软件绘制进度也不是 HDMI 输出的持续物理证明。原有五个 CDC 不安全端点、有限 12 事件队列、未传出 DDR 图像掉电丢失和 HDMI 上一帧红框等限制保留。

下一步优先对持久化证据的完整性和崩溃边界做专项审查，尤其是原图、掩码、元数据、确认日志跨多个文件时的恢复一致性；先复现边界，再分小版修正。传输继续保留安全缓存所有权，任何提速都需实测耗时、丢失率和 CRC，而不是直接提高时钟。真实材料盲测与网络可靠性各自报告。
'''
(R/'docs/Tile_V1.28_绘制进度与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text(f'''# TileLab V1.28

已完成请求身份、实际运动绘制、HDMI 帧码及连续最佳证据验收。状态心跳、请求采用、运动进度和板端完整帧健康分别显示。正常启动不启用诊断冻结。

FPGA 检测硬件继承 V1.24，Vitis 业务逻辑保持 V1.26，固件身份 0x11c00。默认仅预览、归档上限 1 GiB。完整结果见 [实板报告](docs/Tile_V1.28_绘制进度与实板报告.md) 和 DELIVERY_MANIFEST.json。旧工程和备份保留。

Vivado `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`；下载 `.sdk/program_ethernet.bat`，启动工作台 `host/start_station.ps1`。
''',encoding='utf-8')
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.28 实板验证</title><style>body{{margin:0;background:#eef5f5;color:#163e47;font:16px/1.8 system-ui}}main{{max-width:980px;margin:30px auto;padding:32px;background:white;border-radius:20px}}a{{color:#087d80}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{padding:18px;background:#edf7f5;border-radius:12px}}b{{display:block;font-size:30px}}.note{{padding:20px;background:#fff2e2;border-left:4px solid #b8792d}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{margin:0;padding:20px}}}}</style><main><a href="/">← 检测工作台</a><p>V1.28 · 实板验收完成</p><h1>有状态更新，也要有画面进展</h1><p>请求采用、WPF 实际绘制和开发板完整帧健康分别监测。静态图片无需运动检查；相同画面重复刷新不能冒充动画前进。</p><div class="grid"><div class="card">冻结后识别卡顿<b>{r['stall_detection_delay_seconds']:.2f} 秒</b>状态报告仍然新鲜</div><div class="card">冻结时真实 HDMI 抽样<b>{len(r['held'])} 张一致</b>帧码、PNG、CRC 三项一致</div><div class="card">正常运动最佳证据<b>{c['saved']} 个产品</b>居中偏差 ≤ {identity['max_center_error_px']} px</div></div><h2>对真实播放器做了有界故障注入</h2><p>动画停住 8 秒时，开发板仍完整采集 {r['complete_frames_during_hold']} 帧。工作台正确提示缺少绘制进展；同名重选没有隐藏卡顿。恢复后实际 HDMI 帧码继续变化。测试结束恢复正常播放器，仅预览，避免无限落盘。</p><h2>身份和证据链继续通过</h2><p>228 项主机测试、736 组原生解析检查、9 类真实文件争用与播放器重启验证通过。正常连续运动 {c['seconds']:.1f} 秒留存最佳图，掩码、区域框、面积与 CRC 相符。</p><div class="note"><strong>软件绘制进展仍不是持续物理测量</strong><p>故障测试用实板帧码交叉核对；不是拔线或掉电测试。本版未改变检测算法，也没有新准确率或提速结论。跨材质误报、真实相机与既有 CDC 限制保留。</p></div><p><a href="/api/benchmark">完整验收 JSON</a> · docs/Tile_V1.28_绘制进度与实板报告.md</p></main></html>'''
(R/'host/benchmark.html').write_text(html,encoding='utf-8');print('Published measured V1.28 report and verification page')
