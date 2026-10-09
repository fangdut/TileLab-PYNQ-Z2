"""Write acceptance only from this release's completed evidence."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
n=read(O/'queue_wrap_native.json');w=read(O/'wrap_board/summary.json');z=read(O/'zero_restart/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
assert all(v['passed'] for v in (n,w,z,fw,t,f,r,c,a,b,ui,dc,sc)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 128 tests' in units and units.rstrip().endswith('OK')
summary=dict(version='V1.17',passed=True,firmware=fw,queue_native=n,queue_board=w,zero_restart=z,unit_tests=128,
             transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,
             hardware_origin='Unchanged, hash-verified V1.15 BIT/XSA/LTX; inherited V1.16 IRQ preservation; no new place-and-route or accuracy claim')
(O/'queue_wrap_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
jrows='\n'.join(f"| {p['event']} | {p['slot']} | {p['bytes']:,} | {p['elapsed_ms']/1000:.3f} |" for p in w['jtag'])
doc=f'''# Tile V1.17 事件编号回绕与实板验收报告

## 产品和本版成果

项目已形成一个面向连续运动瓷砖的 FPGA 裂纹候选检测演示系统：电脑提供真实瓷砖照片组成的连续运动 HDMI 输入，FPGA 逐像素检测并标红框，板端为每块缺陷瓷砖保留最佳完整帧，网口传给电脑保存和人工复核。它仍是比赛原型，不是已经经过工厂盲测的成品。

本版集中修复长时间运行时的事件编号回绕，不改变识别算法。旧版本有两个可复现缺陷：容量 12 的队列用 32 位编号直接取模，在回绕附近未满就覆盖旧证据；编号 0 的真实事件无法确认。新版本用独立物理读写索引，并允许零事件及其重复确认。128 项主机回归、实际 C 边界/随机试验和实板跨零取图、确认、重启恢复均通过。

## 工程与回退

新工程：D:/Vivado/pynq_z2_tile_v1_53。Vivado 文件为 pynq_z2_tile_v1_53.xpr；Vitis workspace 为 pynq_z2_tile_v1_53.sdk。V1.16 原工程保持，另有 D:/Vivado/_baseline_backups/tile_v1_16_before_v1_17.zip，源码和下载文件可回退；ZIP 未重复囊括海量运行缓存。

本版建立正常 Vivado 工程结构并完整构建 Vitis 平台/应用。PL 源码、约束、BIT/XSA/LTX 与 V1.15 相同，沿用其通过的实现。没有把 prepare-only 当作新的综合、时序或布局布线结论。V1.16 的 IRQ 浮点上下文保护、4 KiB IRQ 栈及整数 memcpy 在实际 V1.17 ELF 中再次核对。

## 硬件、Vitis 和电脑分别做什么

FPGA 硬件负责 720p60 像素流处理：灰度、方向暗谷响应、双阈值邻域支持、区域框、产品跟踪、最佳帧选择信息、像素/描述 CRC。时钟仍是输入恢复的 74.25 MHz 像素时钟，串行发送采用 5 倍时钟加双沿，控制与参考域保留现有配置；本版没有提高频率。

Vitis/ARM 负责 32 描述 DMA 环、48 个 DDR 图像槽、12 条待确认事件、引用所有权、自适应无损压缩、以太网、中断保护和业务确认。本版增加独立 read_pos/write_pos；元数据由 64 增为 66 个 32 位字，增加 8 字节，原 TCP 276 字节头不变。ARM 不进行裂纹分割或重新识别。

电脑工作站负责预览、接收校验、同帧复核框、PNG/数据库保存、容量上限与待确认恢复。本版还修正 JTAG 调试：读取实际队列物理位置、零事件确认的模 2³² 比较、48 槽完整地址范围，以及按实际下载的 hdmi_ethernet ELF 核对登记哈希。

## 先证明旧代码确实失败

旧版实际 C 队列头从 4294967292 开始，入队 5 次后，队首期望编号 4294967293、标记 100，却读到编号 1、标记 104；深度只有 5。另一反例是在 head=4294967295 后发布事件 0，ACK=0 后深度仍为 1。

新 C 代码与独立 Python deque/引用计数模型逐操作对照，通过 {n['boundary_events']} 条确定性边界事件、{n['random_operations']:,} 次随机操作、{n['sequence_crossings']} 次计数回绕，覆盖全部 {n['all_physical_start_positions']} 个物理起始位置、满队列拒绝、重复确认和共享帧槽释放。它是实际 C 的功能测试，不是 ARM 性能测量。

## 实板跨零与慢速调试验证

通过 ARM 编译器导出实际结构偏移，绑定本版 ELF/头文件哈希；硬件断点停在网络/DMA 启动前，检查队列、DMA 与引用为空，然后注入起始 head/tail=4294967288。真实 HDMI 输入和正式固件产生连续 {w['events']} 条事件，从 4294967289 跨过 0 到 12。每条 RAW 与压缩数据全字节相同，三类校验均有效；重复确认不增错误。零事件另外通过 JTAG 确认两次。

| JTAG 事件编号 | 实际图像槽 | 完整字节数 | JTAG 秒数 |
|---:|---:|---:|---:|
{jrows}

JTAG 全帧与网口原始数据、描述信息、像素 CRC 一致，覆盖旧上界以外的实际槽。慢速 JTAG 仅供调试；不能用其耗时评价网口速度，也不宣称日常 JTAG 接口已返回与 TCP 完全相同的 CRC 协议字段。

另对真实事件 0 做三种持久恢复：已保存但 ACK 前进程退出、ACK 已生效但本地尚未结算就退出、保留待确认记录后实际 JTAG 重载板卡。均保留唯一原图和人工复核信息，重启后零次重新取图；第三种先验证 boot_id 变化，记录无法确认旧板端事件，不误把新启动的 head=0 当成旧事件已确认。

每轮边界诊断结束均重新下载未注入计数的正式 BIT/ELF。断点、重载和慢速诊断区间不计入正常连续性能窗口。这里是受控边界验证，不是几年的连续老化证明。

## 普通链路与数据量回归

实际 C 的 3000 个描述 CRC 对照、1280 个单比特错误拒绝和帧槽/SG 所有权回归通过。50 对真实事件 RAW/无损压缩的全图字节一致；9 类网络/数据故障、3 类普通重启与正式 UI 恢复通过。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体减少 % |
|---|---:|---:|---:|
{rows}

连续运动 {c['seconds']:.3f} 秒，主机取图 {c['host_captures']} 次，保存 {c['saved']} 张不同缺陷瓷砖的最佳完整证据，最大居中误差 {a['max_center_error_px']} 像素。图像掩码、框、面积与独立参考一致；验收窗口未新增采集间隙、无效帧、队列丢失、ACK 或描述 CRC 错误。

冻结桌面预览但继续收事件，应用层接收字节率下降 {b['received_rate_reduction_percent']:.3f}%，预期 10 条事件均保留。该指标包括应用响应头，不含以太网/TCP/IP 开销；桌面取样帧率不等于 FPGA 的 60 fps。

主档保留 24 张自动证据与 1 张 UI 恢复证据；边界试验使用隔离目录。验收后恢复连续真实照片输入、仅预览、1 GiB 存档上限。持续预览不无限累积截图。

## 测试中修正的事项

新增两个 JTAG 登记测试最初缺少临时 host 目录，导致 FileNotFoundError；已修正夹具并重跑全部 128 项通过。首轮边界下载后紧接取图出现连接重置，脚本完成干净固件恢复；原始日志保留。零事件重启试验还发现诊断子程序会在工作站仍处于自动恢复时过早退出，已改为遵守现有 30 秒有界恢复、40 秒诊断总上限，非恢复类错误仍立即失败。后续边界测试保留逐事件进度和失败信息，只有完整通过的运行进入上述结果。未把一次重试成功解释为所有 USB/网络故障已经消除。

## 操作方法

1. 电脑 HDMI 720p60 → PYNQ-Z2 HDMI IN；板卡 HDMI OUT → 显示器；PROG UART USB 数据线和直连网线保持连接。
2. 使用同版 .sdk/program_ethernet.bat 下载，再运行根目录“启动以太网工作站.bat”。界面应显示 V1.17；确认来自同一次启动的像素/描述/头部校验。
3. 日常使用选择真实照片连续输入与相应阈值配方。需要保存时选择存档模式；只展示时使用仅预览。冻结预览后仍继续收缺陷事件。
4. 回退先停止当前工作站，再下载并启动完整 V1.16；不要混用各版本 ELF 和调试脚本。program_queue_seed.tcl 是维护诊断入口，不是日常下载脚本。

## 下一步与边界

验收期间的只读 C 审计又复现了一个独立问题：在空队列提前发送下一事件的 ACK，会让 last_ack 提前前进；真正事件后来入队后，同值合法确认被误认为重复。正常工作站按“取图→保存→确认”顺序不会主动触发，但非法/失序请求可能触发。证据见 premature_ack_audit.json；下一版先用这个失败对照修复确认入口，不把新发现掩盖在通过结论里。

随后做 HDMI 输入消失、DMA 停滞/错误后的有界恢复和可见状态，保持已保存及待确认槽不被重用；需要受控故障注入和恢复后的完整图像验证。再处理现有 5 个 CDC 不安全端点、完整帧/产品/存档身份回绕和高速居中偏差。

本版没有把所有身份扩展到 64 位。事件号完整循环后，同一 boot_id 内的历史键仍可能重用；产品/帧编号、不同材料弱裂纹误报、HDMI 前一帧框、有限 12 事件缓存、掉电丢失未存 DDR、单接收端、PNG/SQLite 非跨文件事务仍是边界。CRC 检测偶然损坏，不提供身份认证。

原理与公式见 docs/V1.17_队列回绕与确认原理.md，原始数据与最终哈希见 reports/v132 和 DELIVERY_MANIFEST.json。
'''
(R/'docs/Tile_V1.17_队列回绕与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.17

事件队列使用独立物理索引，修复 32 位回绕覆盖与 ACK=0；JTAG 调试适配 48 槽与实际以太网 ELF。

- Vivado：pynq_z2_tile_v1_53.xpr；PL 沿用哈希相同的 V1.15 实现。
- Vitis workspace：pynq_z2_tile_v1_53.sdk；下载 program_ethernet.bat，完整构建 build_ethernet.py。
- 启动：根目录“启动以太网工作站.bat”；默认仅预览、1 GiB 存档上限。
- 验收：128 项主机回归、12 万次 C 操作、真实跨零与重启、传输/故障/连续留图。
- 报告：docs/Tile_V1.17_队列回绕与实板报告.md；原理：docs/V1.17_队列回绕与确认原理.md。
- 产品现状、三部分职责、优缺点与答辩重点：docs/当前产品与后续路线.md。
- 保留完整 V1.16 与备份 ZIP。板卡诊断种子脚本不用于日常下载。

本版改善可靠性，没有新增检测准确率结论；仍需 HDMI/DMA 自动恢复、CDC、长期身份和独立工厂数据验证。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.17 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.17 / 事件编号回绕</p><h1>编号回到零，证据继续有序确认</h1><section><strong>120,000 次 C 操作 + 20 条实板跨界事件</strong><p>旧代码覆盖与 ACK=0 反例已复现；独立物理索引与零事件确认通过。实板跨界使用受控初始计数注入，不冒充多年老化。</p></section><section><h2>保存、确认与重启一致</h2><p>128 项软件回归；零事件的 ACK 前退出、ACK 后退出、板卡重载三种恢复通过，零次重新取图。JTAG 与 TCP 完整字节一致，覆盖 48 槽区域。</p><p>50 对图像、9 类故障、正常重启与连续留图通过。最大居中误差 {a['max_center_error_px']} 像素，后台字节率下降 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>明确验证范围</h2><p>FPGA 沿用 V1.15，继承 V1.16 中断保护。本版没有新的准确率或时序结论。HDMI/DMA 恢复、CDC、完整身份周期和独立材料盲测仍待处理。</p><p>默认仅预览，存档上限 1 GiB。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.17 report generated from passing fresh evidence')
