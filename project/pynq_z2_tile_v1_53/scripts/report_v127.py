"""Generate the release report only after fresh V1.27 acceptance passes."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_26'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=dict(firmware='firmware_audit.json',parser='native_stimulus/summary.json',stimulus='stimulus_board/summary.json',transport='transport_comparison.json',station='station_continuous.json',identity='station_identity_audit.json',readiness='boot_readiness.json')
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
log=(O/'host_tests.log').read_text();assert 'Ran 206 tests' in log and log.rstrip().endswith('OK')
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');station=s['station'];sync=s['stimulus'];identity=s['identity']
summary=dict(version='V1.27',passed=True,unit_tests=206,**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),
    inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Unchanged PL detector; historical accuracy is not a new blind test'),
    test_scope='Fresh host, parser, actual WPF identity/locking/restart, same-event transport and continuous board evidence tests. Prior V1.26 network fault injections were not all rerun.',limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
cases='\n'.join('- '+name+'：通过。' for name in sync['cases'])
doc=f'''# Tile V1.27 输入请求身份与播放器同步实板报告

## 本版交付与产品分工

V1.27 为电脑发出的每次 HDMI 测试素材选择分配唯一请求编号，并要求当前播放器明确回报这个编号。即使两次都选择同一个视频，也不会用上一请求的状态冒充本次确认；正常运动时间线保持连续。播放器重启后有新的启动身份，旧状态文件不能替代新播放器的报告。

FPGA 产品仍是 720p60 流式裂纹候选检测与证据选择电路：四方向暗谷、双阈值、四级邻域支持、区域框、产品跟踪、最佳帧和原始 CRC。每像素一拍，像素时钟 74.25 MHz。本版没有修改 PL 算法、时钟或位流，不声称重新改善识别准确率。

Vitis 产品仍是板端采集与传输固件：DMA、48 个帧槽、12 个待确认事件、完整帧校验、限定次数恢复、RAW/RLE/PACK25 无损网络传输。只更新版本身份到 0x11b00，完整重建平台、BSP 和 ELF；源码审核确认逻辑与 V1.26 一致。电脑工作台提供请求确认、原图与同帧红框、CRC、按产品留图、人工复核和有界存档。

## 修改内容及原理

命令文件从单纯素材名称升级为最多 128 字节的 ASCII 行：

`TILE_CMD_V1 <32 位小写十六进制请求编号> <素材名称>`

请求编号由 16 字节随机数生成，包含 128 位空间；不是密码或访问凭证。素材名必须属于固定目录清单，不能传任意路径或代码。Python 和实际 WPF 播放器使用的 C# 解析器都检查格式、长度和目录范围。原子替换文件，使读者看到完整旧文件或完整新文件。替换与读取仍可能发生 Windows 文件共享冲突，因此需要显式异常处理。

播放器每次启动生成新的 session，并写入 player_instance.json，包含 PID 和启动时间。player_status.json 报告已采用的 request_id、session、PID、素材、阶段、时间和帧数。状态接口有界读取两个文件，复读启动身份以发现读取中的变化，最后复读命令，避免把读到一半时已更新的请求当作已确认。

确认需要：命令合法，状态新鲜且不报错，素材相同，状态时间不早于命令，处于可用阶段，请求编号完全相同，session 和 PID 与启动标记一致。状态超过 1.5 秒显示过期；超前超过 0.5 秒显示时间不确定。旧式名称命令仍能播放，但显示 LEGACY_UNCONFIRMED。缺文件、乱码、超长文件和文件锁都不会使工作台状态 API 崩溃，也不会主动停止板端接收。

同名新请求仅更新已采用编号，不重新调用运动源 Start。因此用于确认的操作不会重新开始传送带。切换到不同素材才重新加载对应源。本机原生测试发现超长文件抛出的 InvalidDataException 需要单独捕获；修正后再在真实播放器中注入超长命令和乱码，确认视频与采集继续运行。

## 本版实际完成的验证

主机单元测试 **206 项**通过。真实 C# 文件编译后完成 **{s['parser']['catalog_parsing_cases']} 组**正常/非法命令检查，以及真实独占锁、损坏 UTF-8、长度边界、原子替换和播放器脚本语法检查。

真实工作台、WPF 播放器、Windows 文件锁和开发板完成 **{sync['case_count']} 类**专项检查：

{cases}

其中同一运动视频连续选择 10 次，请求编号各不相同，播放器位置和渲染数持续向前。保留真实旧状态文件后发出同名新请求，界面进入等待确认、随后过期；释放文件锁后才确认新编号。独占命令、状态和启动身份文件时，HTTP 仍可读，开发板采集仍推进。实际终止并重启本版播放器，同时保留其旧报告，新进程报告恢复后才确认当前身份。不是用伪造 JSON 冒充实板或播放器结果。

这些专项检查期间板端完整采集增加 **{sync['captured_delta']} 帧**，主机接收增加 **{sync['host_capture_delta']} 张**，没有新增 gap、invalid、drop、ACK 或描述 CRC 错误，未增加自动存档。

同一事件 RAW、原游程自适应、可选位打包三种模式完成 **{s['transport']['byte_exact_triplets']} 组**逐字节对照，并验证实际部分载荷断开后同事件重读。三个 CRC、原图和描述一致。这是对新的输入命令路径的传输回归，不是本版网络算法提速结果。

连续移动真实照片 **{station['seconds']:.3f} 秒**，主机抽样 **{station['host_captures']} 张**，按产品保存 **{station['saved']} 个**缺陷的最佳图；最大居中偏差 **{identity['max_center_error_px']} 像素**。保存图的掩码、框和面积与参考模型一致，产品身份无重复、已观测到的缺陷产品无遗漏，三个 CRC 均通过。参考模型只用于验收，生产检测仍由 FPGA 完成。

一次播放器重启试验中，新播放器已启动，但测试进程在收集启动子进程输出时等待管道结束，导致测试持有的旧状态文件锁没有及时释放。该次没有计为通过，记录保留在 stimulus_board/harness_restart_pipe_wait.json。将测试子进程输出改为直接写日志文件后，重新完成全部九类专项检查；生产播放器和采集接口没有因此更改。此处修正的是测试驱动，不能当作新增检测能力。

Vitis 完整构建后审核实际 ELF：保留浮点中断上下文、4096 字节 IRQ 栈和整数 memcpy。ELF SHA256：`{s['firmware']['elf_sha256']}`。BIT、XSA、LTX 与前版逐字节相同；本版建立可打开的 Vivado 工程，但没有把继承的综合/时序报告冒充新一次实现。

本版没有重复 V1.26 全部网络故障和 DDR 注错项目。其代码逻辑保持一致，历史证据在旧工程；本版新验收和继承结论明确区分。

## 运行、回退与空间

工程：`{R.as_posix()}`。Vivado 入口 `{R.name}.xpr`，Vitis workspace `{R.name}.sdk`。USB 接 PROG UART；电脑 HDMI 接 IN、OUT 接显示器；以太网直连电脑，板端 169.254.200.10，720p60。

停止旧工作站后，用本版 `.sdk/program_ethernet.bat` 下载匹配 BIT 和 ELF，随后 `host/start_station.ps1`。默认仅预览；自动留图上限 1 GiB，测试只在有界时间开启。V1.26 原工程保留，备份 `{plan['backup']}`，SHA256 `{plan['backup_sha256']}`。轻量 ZIP 包含源码、文档、关键下载文件；完整运行记录和素材保留在原工程。

界面“播放器已回报请求编号”只表示本机软件已采用输入，不能代替 HDMI 电缆、开发板帧计数或外接显示器的观察。session/PID 文件用于协作进程的一致性检查，不是防伪认证。1.5 秒新鲜窗口内的报告也不是进程仍存活的数学证明，时钟变化可能让确认暂时退回等待。

## 优势、限制与下一步

相同素材重选、文件争用和播放器重启有明确身份；不让旧报告误导使用者，不以等待用户代替自动测试。改动范围只围绕输入同步，保留已验证采集链路和回退版本。

仍需改进：状态更新时间不能直接证明画面在运动；下一版优先区分“状态心跳正常”和“渲染帧确实前进”，只对运动源判断，静态图片不能误报卡住，并测试计数复位、暂停和不同视频阶段。再评估安全复制开销和高速度最佳帧偏差。跨材质误报、弱裂纹剩余漏检、真实相机曝光/运动模糊仍是产品化主要缺口。

V1.24 的开发集弱裂纹像素召回提升约 3.75 个百分点，但跨材质正常屋面图仍有大量误报，不能宣传通用工业准确率。五个既有 CDC 不安全端点、有限事件队列、未传出的 DDR 证据掉电丢失、HDMI 使用上一帧红框等限制未在本版消除。无损省流 21.875% 是格式负载比例，不等于网口必然更快，更不等于检测精度提高。
'''
(R/'docs/Tile_V1.27_输入身份与同步实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text(f'''# TileLab V1.27

已完成构建、请求身份/文件争用/播放器重启专项实板测试和连续移动留图验收。新增每次输入请求的唯一编号、播放器启动身份核对；同名视频重选保持时间线。

FPGA 检测硬件继承 V1.24；Vitis 逻辑继承 V1.26，固件身份 0x11b00。默认仅预览，归档上限 1 GiB。完整结果和局限见 [实板报告](docs/Tile_V1.27_输入身份与同步实板报告.md) 与 DELIVERY_MANIFEST.json。输入确认是本机软件采用报告，不等于物理 HDMI 链路确认。

Vivado 打开 `{R.name}.xpr`，Vitis 工作区 `{R.name}.sdk`。下载入口 `.sdk/program_ethernet.bat`，工作台启动 `host/start_station.ps1`。旧工程和备份保留。
''',encoding='utf-8')
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.27 验证</title><style>body{{margin:0;background:#eef5f5;color:#163e47;font:16px/1.8 system-ui}}main{{max-width:980px;margin:30px auto;padding:32px;background:white;border-radius:20px}}a{{color:#087d80}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{padding:18px;background:#edf7f5;border-radius:12px}}b{{display:block;font-size:30px}}.note{{padding:20px;background:#fff2e2;border-left:4px solid #b8792d}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{margin:0;padding:20px}}}}</style><main><a href="/">← 检测工作台</a><p>V1.27 · 实板验收完成</p><h1>每次输入请求，都有对应确认</h1><p>同名视频重新选择时，播放器回报新的请求编号，运动时间线不重置。启动身份与报告分开核对，旧文件不代替新播放器的确认。</p><div class="grid"><div class="card">实际同步故障场景<b>{sync['case_count']} 类</b>文件锁、损坏命令、重启</div><div class="card">连续运动留图<b>{station['saved']} 个产品</b>{station['seconds']:.1f} 秒，居中偏差 ≤ {identity['max_center_error_px']} px</div><div class="card">本机验证<b>206 + 736</b>主机测试 + 原生解析样例</div></div><h2>没有把命令写入当作播放成功</h2><p>请求编号、素材名、播放器 session/PID、阶段和时间一致才确认。过期、旧式命令、文件占用均有明确状态。十次同名选择，画面运动继续；九类专项检查时实板完整采集增加 {sync['captured_delta']} 帧，无新增采集/确认错误。</p><h2>检测与证据链继续通过</h2><p>50 组三种格式同事件对照，原图、掩码、描述和 CRC 一致；60 秒真实照片连续运动，按产品保存最佳图并核对框、掩码和面积。FPGA/Vitis 检测与传输逻辑未改动。本版没有新的准确率或提速结论。</p><div class="note"><strong>本机输入确认 ≠ 物理 HDMI 确认</strong><p>状态新鲜也不直接证明画面在运动；下一版继续完善渲染进度监测。跨材质误报、真实相机和既有 CDC 限制仍然保留。</p></div><p><a href="/api/benchmark">查看完整验收 JSON</a> · docs/Tile_V1.27_输入身份与同步实板报告.md</p></main></html>'''
(R/'host/benchmark.html').write_text(html,encoding='utf-8');print('V1.27 measured report and verification page published')
