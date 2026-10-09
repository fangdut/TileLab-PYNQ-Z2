"""Publish V1.31 only after fresh implementation and real-board evidence pass."""
from pathlib import Path
import json, hashlib

R = Path(__file__).resolve().parents[1]
O = R / 'reports/v132'
B = R.parent / 'pynq_z2_tile_v1_30'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

files = dict(source='source_audit.json', hardware='hardware_audit.json',
             firmware='firmware_audit.json', review_session='review_session_native.json',
             readiness='boot_readiness.json', real='real_board/summary.json',
             transport='transport_comparison.json', station='station_continuous.json',
             identity='station_identity_audit.json')
s = {k: read(O / v) for k, v in files.items()}
assert all(v['passed'] for v in s.values())
log = (O / 'host_tests.log').read_text()
assert 'Ran 265 tests' in log and log.rstrip().endswith('OK')
assert s['review_session']['tests'] == 19
assert s['real']['samples'] == s['real']['pixel_exact'] == 50
assert all(r['baseline_rgb_mismatch'] == 0 for r in s['real']['items'])
assert s['transport']['byte_exact_triplets'] == 50
assert s['transport']['packed_reconnect_same_event']
assert s['hardware']['cdc_unsafe_endpoints'] == 0
assert s['station']['saved'] == s['identity']['physical_products'] == 10
plan = read(R / 'ITERATION_PLAN.json')
old = read(B / 'DELIVERY_MANIFEST.json')
# Resolve superseded limitations explicitly; keep physical-test boundaries.
limits = []
for limit in old['limits']:
    if limit.startswith('Five original CDC'):
        limits.append('V1.31 routed report has zero unsafe CDC endpoints; residual I/O timing/methodology warnings require separate review. CDC structure is not a physical hotplug or metastability proof.')
    elif limit.startswith('Player READY is local telemetry'):
        limits.append('V1.27 command/session identity and V1.28 drawing progress are local telemetry; ongoing physical HDMI authentication remains absent.')
    elif limit.startswith('V1.29 verifies'):
        limits.append(limit.replace('Concurrent review edits remain to be guarded.', 'V1.30 guards concurrent review revisions; full reviewer identity/history is absent.'))
    else:
        limits.append(limit)
summary = dict(version='V1.31', passed=True, unit_tests=265, **s,
               baseline_manifest_sha256=sha(B / 'DELIVERY_MANIFEST.json'),
               test_scope='Fresh reset simulation, routed timing/CDC/netlist, full Vitis build, JTAG programming, 50-photo real HDMI RGB/mask/box regression, 50 three-codec comparisons and packed retry, continuous best-evidence validation. No physical cable/power removal.',
               limits=limits)
(O / 'packed_validation_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
h = s['hardware']; c = s['station']; i = s['identity']; r = s['real']; q = s['source']['reset_simulation']
transport_rows=[]
for name,entry in s['transport']['summary'].items():
    a,b,d=(entry[k] for k in ('raw','legacy','compact'))
    transport_rows.append(f"| {name} | {a['request_ms']:.3f} | {b['request_ms']:.3f} | {d['request_ms']:.3f} | {b['wire_payload_bytes']:,.0f} | {d['wire_payload_bytes']:,.0f} |")
transport_table='\n'.join(transport_rows)
report = 'docs/Tile_V1.31_共享复位同步与实板报告.md'
doc = f'''# Tile V1.31 共享复位同步与实板报告

## 做成了什么

本版修改 FPGA 的 HDMI 接收复位结构，完成新的综合、布局布线、BIT/XSA 导出、Vitis 完整重建和真实开发板下载。旧版 routed 检查点中的 **5 个 CDC-11 不安全端点，本版降为 0**。没有降低时钟、放宽顶层时序约束或加入 CDC 豁免。

产品仍是 HDMI 输入的瓷砖裂纹候选检测与证据工作站：FPGA 完成图像流水线、四级弱裂纹邻域支持、候选框、产品跟踪、最佳证据与 CRC；ARM/Vitis 管理 DMA、帧槽、事件队列、确认和无损网络发送；电脑负责接收、证据一致性、存档、人工复核与播放器。本次不改检测阈值或算法，不把复位可靠性改进当作识别精度提升。

## 先定位旧结构，再修改

重新只读打开 V1.24 的真实 routed DCP。前两项 CDC-11 来自 200 MHz 的 aLocked 向 RX、检测核心、TX 三条像素复位同步链扇出；另外三项来自像素复位向三个颜色通道各自的参考域 SourceResetBridge 扇出。原设计已经能正常显示与检测，告警表示需要审查的电路结构，不能据此编造已发生的画面故障。

新增 DecoderResetDomains：原始锁定信号只进入一个共享像素复位同步器；其输出再进入一个共享 200 MHz 参考域复位同步器。三个解码通道共用相应域复位。aPixelClkLckd 对外表示经过像素域确认的 PixelReady，失锁时异步拉低，重新升高须等待像素时钟。外部 Block Design 端口保持兼容。

SyncBase 明确接收 iReset、oReset 两个本域复位，保留源登记和目标同步触发器，移除重复 SourceResetBridge。相应源登记触发器的一条旧复位假路径被移除，让工具实际检查 recovery/removal。生成 IP 中的源码、XDC 与作者修改稿逐一核对，避免只改了库文件却编译缓存旧电路。

共享的是跨异步域的入口；检测核心和发送器仍保留固定的本地复位延迟，所以并不声称所有模块在同一个周期离开复位。主要风险是独立跨域同步链可能在不同周期作出释放决定；共享入口消除了这组重复跨域路径。[AMD UG906 异步复位同步器说明](https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/Asynchronous-Reset-Synchronizer)

## 时钟、实现和资源

像素 74.25 MHz、AXI 100 MHz、参考 200 MHz 保持不变，处理吞吐仍为每像素时钟一个像素。TX 串行时钟仍为像素时钟的 5 倍并双沿发送；本次不靠提高频率解决可靠性。

| 检查 | V1.31 实测 |
|---|---:|
| WNS，最差建立时间余量 | {h['wns_ns']:+.3f} ns |
| WHS，最差保持时间余量 | {h['whs_ns']:+.3f} ns |
| WPWS，最差脉宽余量 | {h['wpws_ns']:+.3f} ns |
| Slice LUT | {h['resources']['Slice LUTs']:g} |
| Slice Register | {h['resources']['Slice Registers']:g} |
| BRAM Tile | {h['resources']['Block RAM Tile']:g} |
| DSP | {h['resources']['DSPs']:g} |
| 不安全 CDC 端点 | {h['cdc_unsafe_endpoints']} |
| 满足约束的总线偏斜路径组 | {h['bus_skew_constraints_met']} |

本版网表核对共享像素和参考同步器各两级、ASYNC_REG 属性保留、重复 SourceResetBridge 为零。参考域与像素域各三个源登记复位路径实际存在，recovery 和 removal 两类检查均满足约束；没有只靠报告统计清零。BIT 与实现目录、XSA 内嵌 BIT 字节一致。零不安全 CDC 只是工具在当前约束与可识别结构下的结果，不是亚稳态永不发生的证明。

## 逐步测试记录

1. 实际 VHDL 模块专项仿真：{q['phase_sweeps']} 组释放相位、{q['stopped_clock_scenarios']} 种时钟停止情形、{q['crossings']} 条跨域路径、{q['checks']} 项检查通过。验证失锁立即进入复位、停止时钟不能提前释放、数据最终正确到达。数字模型不能模拟真实亚稳态或 HDMI 电气行为。
2. 主机 **265 项**回归及实际 ReviewSession 类 **19 项**测试通过。复核并发和存档逻辑没有新增功能；本次未重复全部旧浏览器故障和 SQLite 强制退出专项。
3. 完整 Vivado 实现、DRC、时序、CDC、总线偏斜与网表审查通过。使用顺序 OOC 构建及两个通用线程，避免此前并行工具崩溃的已知环境问题。顶层综合曾出现两条与 V1.24 相同的严重警告：尚未展开 PS IP 时找不到 PS 时钟，时钟组暂不能求值；本版保留日志，并在完整实现网表重新检查 100/200/74.25 MHz 时钟对象与实际约束。没有声称整个构建日志零警告。
4. 完整 Vitis 平台/BSP/应用重建。业务代码与 V1.30 相比仅版本及注释变化；固件身份 0x11f00。ELF 反汇编再次检查中断浮点保存、4096 字节 IRQ 栈和整数 memcpy。真实 JTAG 下载后核对启动身份、版本与完整采集帧。
5. **50 张历史真实瓷砖照片经实际 HDMI→FPGA→TCP 重新采集**：RGB 分量与 V1.24 的同图实板原图逐分量相等；掩码与同图参考模型逐像素相等，区域框/面积一致。{r['counts']['crack']['alarms']}/{r['counts']['crack']['total']} 张裂纹图触发，{r['counts']['good']['alarms']}/{r['counts']['good']['total']} 张正常图触发。裂纹像素召回 {r['pixel_recall']:.6f}，精确率 {r['pixel_precision']:.6f}，保持既有结果。它们是参与过开发的历史回归集，不能写成工厂盲测准确率。
6. **50 组同一事件 RAW32 / 自适应 RLE / PACK25 三模式对照**：完整解码字节、描述与三层 CRC 相同。真实 PACK25 响应中途断开后重连，仍拿到同一未确认事件；确认后队列才前进。噪声场景 PACK25 有效载荷为 2,880,000 字节，比 RAW32 的 3,686,400 字节减少 21.875%。本版没有传输算法变化，耗时以 JSON 记录为准，不把单轮波动称为提速。
7. 连续运动 **{c['seconds']:.3f} 秒**，主机接收 {c['host_captures']} 张抽样，完整板端采集计数增加 {c['after']['captured']-c['before']['captured']}，经过 {c['after']['products_completed']-c['before']['products_completed']} 个产品，保存 {c['saved']} 个缺陷产品各一张最佳证据。源画面条码核对没有重复或已观察产品漏存，居中偏差最大 {i['max_center_error_px']} px，满足 32 px 目标。原图、掩码、框、区域面积与 CRC 一致，验收区间没有新增采集间隙、坏帧、队列丢弃及确认/描述 CRC 错误。

三模式本次实板测量如下，每场景 10 个同事件样本，表中时间为中位数，包含请求、收取、解码和像素 CRC 检查；不包含摄像头曝光或图像最初被采集的等待时间。字节数为图像有效载荷，不含响应头及以太网/TCP 开销。

| 场景 | RAW ms | RLE ms | PACK 可选模式 ms | RLE 载荷字节 | PACK 模式载荷字节 |
|---|---:|---:|---:|---:|---:|
{transport_table}

PACK 模式也会自适应选择更小的 RLE 数据；模式选择并不意味着每张图都使用 BGR24_MASK1 编码。空场与照片适合 RLE，噪声图适合考察固定打包的体积上限。默认仍为已有自适应 RLE。

## 交付、使用与回退

工程 `{R.as_posix()}`，Vivado `{R.name}.xpr`；Vitis 工作区 `{R.name}.sdk`。下载使用工作区的 program_ethernet.bat，启动使用 host/start_station.ps1。USB 接 PROG UART；电脑 HDMI 接板 IN，板 OUT 接显示器，720p60；网线直连电脑。

BIT SHA256：`{h['artifacts_sha256']['system.bit']}`。

ELF SHA256：`{s['firmware']['elf_sha256']}`。

上一版 `{B.as_posix()}` 保留；轻量备份 `{plan['backup']}`，SHA256 `{plan['backup_sha256']}`。核对旧版 {s['source']['baseline_source_files']} 份清单源码及 {s['source']['baseline_ip_files']} 份 IP 文件未改变。本版交付清单额外覆盖 ip_repo 的 VHDL/XDC/XML 等文件。

回退须先停止当前接收服务，再用旧版匹配 BIT/ELF 下载并启动旧版工作站；不要混用硬件和固件或让两个接收服务争用开发板。测试结束恢复真实照片连续运动、RLE 默认传输、仅预览模式，自动存档上限 1 GiB。此次有限回归证据保留，未删除旧工程。

## 仍然存在的不足和下一步

这次没有执行物理 HDMI 拔插、外部时钟任意丢失或板卡断电试验；数字复位仿真与正常流实板回归不能代替它们。I/O 约束及其他 methodology 警告仍需按具体路径审查，不能因 CDC 变为零就全部忽略。建立/保持余量也不代表现场电压温度下所有系统风险已经覆盖。

检测方面，弱裂纹没有强种子时仍可能漏检，复杂纹理存在显著跨材质误报，仍缺真实相机、曝光和运动模糊验证。HDMI 框采用上一完成帧；电脑证据框与其本帧绑定。高速居中曾有 40 px 超过 32 px 目标的失败案例，正常速度通过不消除该限制。DDR 仅有有限事件队列，未发出证据无法抗长时间停收或掉电。

本轮只读审查还确认，既有八项跨域最大数据路径延迟被顶层异步时钟组覆盖。它们涉及 FIFO Gray 指针和六组握手数据，限制值 10～53.872 ns；总线偏斜满足不等于最大延迟限制已生效。详见 `docs/V1.31_剩余时序约束审查.md`。下一轮优先单独恢复这些约束的实际作用，再检查帧/产品身份在复位与长周期计数边界的一致性，以及输入恢复时的新产品归档边界。新功能仍要保留旧版、独立验证，不在本轮随意叠加。
'''
(R / report).write_text(doc, encoding='utf-8')
(R / 'README.md').write_text(f'''# TileLab V1.31

已完成 HDMI 共享复位同步、完整 FPGA 实现与新 Vitis 构建，真实开发板 50 图与 50 组三模式传输回归、连续运动最佳证据验收通过。详细 CDC 不安全端点由 5 降为 0，没有新增假路径或豁免。

检测算法和 74.25/100/200 MHz 时钟保持。物理热插拔、电源故障和工厂盲测尚未完成。默认仅预览，自动存档上限 1 GiB。详见 [完整报告]({report}) 与 DELIVERY_MANIFEST.json。

Vivado `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`；下载 `.sdk/program_ethernet.bat`，启动 `host/start_station.ps1`。V1.30 工程及独立 ZIP 保留。
''', encoding='utf-8')
html = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.31 实板验证</title><style>body{{margin:0;background:#eef5f5;color:#163e47;font:16px/1.8 system-ui}}main{{max-width:980px;margin:30px auto;padding:32px;background:white;border-radius:20px}}a{{color:#087d80}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{padding:18px;background:#edf7f5;border-radius:12px}}b{{display:block;font-size:30px}}.note{{padding:20px;background:#fff2e2;border-left:4px solid #b8792d}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{margin:0;padding:20px}}}}</style><main><a href="/">← 检测工作台</a><p>V1.31 · 新硬件实板验收完成</p><h1>共享复位入口，明确跨域释放顺序</h1><p>完整重建 FPGA 和 Vitis。保留原来的检测算法与工作频率，移除重复跨域复位链，并恢复源寄存器复位时序检查。</p><div class="grid"><div class="card">不安全 CDC 端点<b>5 → 0</b>没有新增假路径或豁免</div><div class="card">真实照片同图回归<b>50 / 50</b>RGB、掩码与区域框一致</div><div class="card">连续运动最佳证据<b>{c['saved']} 个产品</b>最大居中偏差 {i['max_center_error_px']} px</div></div><h2>结构和时序都有证据</h2><p>两组共享同步器保留各两级触发器；三个参考域复位恢复路径满足时序。WNS {h['wns_ns']:+.3f} ns，WHS {h['whs_ns']:+.3f} ns；8 组总线偏斜约束通过。专项数字仿真 {q['checks']} 项检查、主机 265 项及浏览器会话类 19 项通过。</p><h2>重新烧录后测试完整链路</h2><p>50 张历史真实照片从 HDMI 输入，经 FPGA 计算后从网络取回。另完成 50 组三种传输模式字节对照和一次 PACK25 中断重取；{c['seconds']:.1f} 秒连续运动验收保存每个缺陷产品的一张最佳图。测试后恢复仅预览。</p><div class="note"><strong>零 CDC 告警不等于所有物理故障均已验证</strong><p>未进行物理 HDMI 拔插或板卡断电测试。历史照片回归不代表工厂盲测准确率；跨材质误报、真实相机和高速居中限制仍保留。本版没有新的识别提精度或传输提速结论。</p></div><p><a href="/api/benchmark">完整验收 JSON</a> · {report}</p></main></html>'''
(R / 'host/benchmark.html').write_text(html, encoding='utf-8')
print('Published measured V1.31 report and verification page')
