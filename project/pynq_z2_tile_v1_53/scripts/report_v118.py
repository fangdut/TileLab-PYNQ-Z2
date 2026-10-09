from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
n=read(O/'ack_isolation_native.json');w=read(O/'ack_board/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json');wrap=read(O/'queue_wrap_native.json')
assert all(v['passed'] for v in (n,w,fw,t,f,r,c,a,b,ui,dc,sc,wrap)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 128 tests' in units and units.rstrip().endswith('OK')
run=Path(w['run_directory']);readiness={p.relative_to(run).as_posix():read(p) for p in run.rglob('*video_ready.json')}
assert readiness and all(v[-1]['captured']>=3 for v in readiness.values())
ready_max=max(v[-1]['seconds'] for v in readiness.values())
summary=dict(version='V1.18',passed=True,firmware=fw,ack_native=n,ack_board=w,queue_wrap_native=wrap,video_readiness=readiness,unit_tests=128,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,hardware_origin='Unchanged, hash-verified V1.15 BIT/XSA/LTX; V1.16 IRQ preservation and V1.17 ring indexing retained')
(O/'ack_isolation_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
doc=f'''# Tile V1.18 异常确认隔离与实板验收报告

## 本版成果

修复空队列提前收到未来事件 ACK 后，后续合法确认被误认为重复、事件无法释放的问题。网口和 JTAG 入口先验证请求，固件底层拒绝时消费错误邮箱并恢复已提交状态，要求后续事件收到一次新的合法确认。

这是可靠性改进，视觉检测仍在 FPGA，算法、频率、像素流水线和原图内容没有改变。当前产品仍为真实瓷砖照片经 HDMI 连续运动的检测与复核原型，不能替代工厂相机盲测。

## 保存、构建与改动

V1.17 原工程完整保留，另备份 D:/Vivado/_baseline_backups/tile_v1_17_before_v1_18.zip。新工程 D:/Vivado/pynq_z2_tile_v1_53，Vivado 为 pynq_z2_tile_v1_53.xpr，Vitis workspace 为同名 .sdk。

本版完整构建 Vitis 平台与 ARM 应用，Vivado 建立可打开的工程结构，沿用哈希相同的 V1.15 BIT/XSA/LTX，没有新布局布线或时序结论。实际 ELF 再核对 V1.16 中断浮点现场保护、4 KiB IRQ 栈和整数 memcpy。原工具生成 CMake 的路径警告保留在构建日志中。

- event_queue.h：只有成功确认才能推进 last_ack；拒绝时累计一次错误，将邮箱恢复为 head，防止重复轮询和遗留请求误释放未来帧。
- network.c：错误启动号、空队列未来确认、非队首确认在入口被拒绝，返回带头部 CRC 的错误响应，且不写 ACK 邮箱。
- event_capture.tcl：JTAG 在确认下一事件前要求队列非空，保留跨 0 比较与重复确认行为。
- 主机只更新版本及报告入口，检测、存储、重连和待确认持久化路径保持。

## 先复现旧问题，再验证修复

实际 V1.17 C 在 head=0 和 head=4294967295 两种起点都复现失败：提前 ACK 1 或 0 后，真正同号事件入队，再次合法 ACK 仍无法释放。新 C 通过 {n['boundary_scenarios']} 个场景、{n['random_operations']:,} 次随机操作，覆盖全部物理起始位置、普通/跨零编号、未来/过期/重复请求、队列满、共享槽，以及描述地址异常被修复后重新确认。

另重跑上一版的独立环索引回归：{wrap['boundary_events']} 个边界事件和 {wrap['random_operations']:,} 次操作。两组测试不是两套硬件实现；它们分别检查请求隔离和队列回绕。128 项主机测试全部通过。实际 C 的描述 CRC、1280 个单比特错误拒绝、48 槽与 SG 所有权回归通过。

在实际旧固件运行的开发板上再次复现提前确认卡住，记录原图哈希和带 CRC 的错误回复，然后下载本版固件。新版普通事件及跨零事件各收到 6 个错误网口请求，均拒绝；队首、槽归属、已捕获像素不变，之后合法确认成功，重复确认不二次释放。

零事件另测 JTAG 空队列未来确认拒绝；随后在验证启动号和空队列后，直接向 DDR 确认邮箱写入一个未来 ACK，绕过入口预检查。固件仅累计一次错误并恢复邮箱，真实事件 0 后来入队仍被保留，JTAG 的新合法确认与重复确认、TCP 重复确认均正常。受控诊断不改 DMA 或图像内容，结束重新下载干净正式固件。

首轮在切换工作站进程之后未满足“初始队列为空”的准备条件，尚未执行新版确认验证即停止，并自动重载干净固件。测试脚本已增加准备事件的有界保存与排空，再核对测试起点。旧固件失败反例保留在原始运行目录，后续成功轮引用它并核对旧下载登记的启动号和 ELF/BIT 哈希，没有把不同轮次伪装成同一次运行。另一次初始取图出现连接重置，保留的起始状态显示完整帧计数为 0。已把就绪检查改为等待至少 3 个实际完整帧，记录等待轨迹；网口就绪不等于视频就绪。源码差异审计还修正了预期文本多一个换行的比较错误，实际固件没有因此改动。

本轮下载脚本返回后的诊断就绪检查最长 {ready_max:.3f} 秒，包括网络访问与等待真实完整帧。不能把它解释为每次固定启动时间；后续版本应将这类健康状态提供给工作站，而不是让用户只看到网络超时。

## 连续与故障回归

50 对实际 RAW/无损压缩图像逐字节一致，像素、头部身份和 PL 描述三类校验通过。9 类网络/数据故障、3 类进程退出/实际 JTAG 重载、正式 UI 待确认恢复通过；UI 恢复不重新取图。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体减少 % |
|---|---:|---:|---:|
{rows}

连续运动 {c['seconds']:.3f} 秒，电脑取图 {c['host_captures']} 次，保存 {c['saved']} 张不同缺陷瓷砖的最佳完整图，最大居中误差 {a['max_center_error_px']} 像素。掩码、区域框、面积和来源产品与独立参考一致，正常验收窗口未新增间隙、无效帧、队列丢失、ACK 或描述校验错误。故障注入产生的预期错误计数单独记录，不混入正常窗口。

冻结预览时仍按事件保存，接收字节率下降 {b['received_rate_reduction_percent']:.3f}%，预期 10 个事件均保存。应用层字节统计不包含链路/TCP/IP 开销，也不意味着桌面以 60 fps 显示。验收后恢复连续真实照片输入、仅预览和 1 GiB 存档上限。

## 如何使用和回退

保持 720p60 HDMI 输入/输出、PROG UART USB 数据线和电脑直连网线。使用本版 .sdk/program_ethernet.bat 下载，再启动根目录“启动以太网工作站.bat”。演示选择真实照片连续运动与对应材料参数；需要留图时启用存档，普通观察保持仅预览。

回退先停止本版服务，再下载并启动完整 V1.17。inject_empty_ack.tcl 和计数注入脚本都是维护诊断，不用于日常运行。

## 下一步

先把完整图像就绪与采集停滞做成可见健康状态，再做 HDMI/DMA 错误后的有界恢复，保留待确认证据并核对恢复后的第一张完整图。详细只读审计见 下一版_采集健康度与恢复审计.md。随后处理剩余 CDC、完整帧/产品/存档身份周期和高速居中。算法方向继续做独立材料盲测、弱裂纹/纹理误报的分层统计，再决定多尺度或方向连续性硬件改进。

本版没有解决有限 12 事件缓存、板卡掉电丢失未存 DDR、单接收端、PNG/SQLite 跨文件事务、HDMI 上一帧坐标、中断嵌套最坏栈和材料泛化。CRC 不提供身份认证。原理见 V1.18_异常确认隔离原理.md；上版的完整产品职责与优缺点见 V1.17/docs/当前产品与后续路线.md。
'''
(R/'docs/Tile_V1.18_异常确认隔离与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.18

隔离提前、过期、错误启动号的确认，错误请求不释放证据，也不卡住将来的合法确认。

- Vivado：pynq_z2_tile_v1_53.xpr，PL 沿用已验证 V1.15 文件。
- Vitis workspace：pynq_z2_tile_v1_53.sdk；build_ethernet.py 完整构建，program_ethernet.bat 下载。
- 工作站：根目录“启动以太网工作站.bat”，默认仅预览与 1 GiB 存档上限。
- 报告：docs/Tile_V1.18_异常确认隔离与实板报告.md；原理：docs/V1.18_异常确认隔离原理.md。
- 原 V1.17 工程与备份 ZIP 均保留。

包含实际旧/新固件对照、受控邮箱注入、跨零确认和正常图像回归；仍需 HDMI/DMA 恢复、CDC、长期身份与独立工厂数据验证。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.18 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.18 / 异常确认隔离</p><h1>错误请求，不影响下一条真实证据</h1><section><strong>旧实板失败已复现，新固件确认恢复正常</strong><p>普通与零事件各 6 个错误网口请求；JTAG 拒绝提前确认；直接邮箱注入后要求新的合法确认，不误释放未来图像。</p></section><section><h2>持续采集与保存通过回归</h2><p>128 项主机测试，216 个 ACK 边界场景与 12 万次操作；环索引另有 12 万次回归。50 对真实图像、9 类故障、3 类重启和 UI 恢复通过。</p><p>最大居中误差 {a['max_center_error_px']} 像素，后台字节率下降 {b['received_rate_reduction_percent']:.2f}%。默认仅预览，存档上限 1 GiB。</p></section><section class="warning"><h2>范围</h2><p>本版只改善确认一致性，FPGA 和检测算法保持。HDMI/DMA 自恢复、CDC、长期身份与真实工厂数据仍需完善。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.18 report generated only from passing fresh evidence')
