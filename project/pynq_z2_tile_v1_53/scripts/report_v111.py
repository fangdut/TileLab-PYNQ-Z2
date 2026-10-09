from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
h=read(R/'reports/v132/hardware_crc_check.json')
sim=read(R/'reports/v132/crc_sim_summary.json');native=read(R/'reports/v132/firmware_crc_test.json')
t=read(R/'reports/v132/transport_comparison.json');f=read(R/'reports/v132/recovery/summary.json')
c=read(R/'reports/v132/station_continuous.json');a=read(R/'reports/v132/station_identity_audit.json');b=read(R/'reports/v132/background_summary.json')
assert all(x['passed'] for x in (h,sim,native,t,f,c,a,b))
assert 'Ran 92 tests' in (R/'reports/v132/host_tests_final.log').read_text(encoding='utf-8-sig')
u=(R/'reports/utilization.rpt').read_text()
resources={n:int(re.search(r'\|\s*'+re.escape(n)+r'\s*\|\s*(\d+)',u).group(1)) for n in ('Slice LUTs','Slice Registers','Block RAM Tile','DSPs')}
summary=dict(version='V1.11',passed=True,hardware=h,resources=resources,unit_tests=92,simulation=sim,firmware_native=native,transport=t['summary'],faults=f,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b)
(R/'reports/v132/crc_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join('| '+n+' | '+f"{s['raw_request_ms']:.2f}"+' | '+f"{s['compact_request_ms']:.2f}"+' | '+f"{s['saving_percent']:.2f}"+' | '+f"{s['crc_ms']:.3f}"+' |' for n,s in t['summary'].items())
faults='\n'.join('| '+x['name']+' | '+f"{x['seconds']:.3f}"+' | '+str(x['saved'])+' | '+('恢复成功' if x['recovered'] else '拒收/停止')+' |' for x in f['cases'])
doc=f'''# Tile V1.11 FPGA 整帧 CRC 与可靠传输报告

## 本版做成了什么

V1.11 在已验证 V1.10 上增加从 FPGA 输出到电脑解压的整帧 CRC 检查。FPGA 对每个 B、G、R、mask 字节计算校验值，Vitis 保存并转发，电脑在保存或确认之前核对。原始和压缩传输均覆盖，颜色损坏也能被发现。旧 V1.10 工程完整保留，另有 _baseline_backups/tile_v1_10_before_v1_11.zip 源码及下载文件备份，哈希见 ITERATION_PLAN.json。

这是实际硬件版本：本版重新综合、布局布线、生成 BIT/XSA/LTX，再用新 XSA 重建 Vitis 平台和 ELF，实际 JTAG 下载到 PYNQ-Z2。与 V1.7～V1.10 沿用 V1.6 硬件的情况不同。下载为易失性配置，没有改写板卡 Flash。

## 硬件与 Vitis 各自是什么产品

FPGA 是实时视觉检测和证据生成引擎：HDMI 720p60 输入、四方向暗谷响应、双阈值弱裂纹支持、区域框、产品编号、最佳帧选择，以及本版新增加的像素 CRC，全在可编程逻辑中执行。每个像素进入流水线一次，不需要 ARM 运行视觉算法。CRC 的主计算状态为 32 位，另有固定 XOR 网络、描述锁存和复用逻辑；总开销以实际资源报告为准。

Vitis 工程生成 Cortex-A9 裸机数据服务：32 个预投递 DMA 描述符、48 个 DDR 帧槽、12 个事件缓存、无损编码、网络发送、同一事件确认。本版 ARM 在把 PL 描述字转换为 DDR 地址前保留 CRC，跟随同一帧槽的所有权；不重新遍历图像计算 CRC，也不做裂纹识别。

电脑是接收、复核和证据工作站：解压、CRC 验证、协议/掩码一致性检查、PNG 和 SQLite 保存、人工复核。冻结预览继续后台接收。图像、掩码和红框来自同一帧。独立参考算法只在离线验收脚本中运行，不参与生产识别。

## 时钟、时序与资源

仍使用 HDMI 恢复的 74.25 MHz 像素时钟、100 MHz DMA/AXI 时钟、200 MHz HDMI 参考时钟，未提高工作频率。CRC 使用像素时钟，未新增跨时钟数据通道。

- 全设计 WNS：{h['setup_wns_ns']:+.3f} ns；WHS：{h['hold_whs_ns']:+.3f} ns。
- CRC 寄存器输入最差 setup slack：{h['crc_setup_slack_ns']:+.3f} ns；网表检查有 {h['crc_registers']} 个 CRC 寄存器。
- LUT：{resources['Slice LUTs']}（V1.6 为 16793）；FF：{resources['Slice Registers']}（V1.6 为 28292）。
- BRAM tile：{resources['Block RAM Tile']}；DSP：{resources['DSPs']}。

全局 hold 余量仅 0.011 ns，虽然满足当前约束，仍是后续物理实现可改进的地方。时序正余量不能当作全部 CDC 已解决：两组 HDMI 时钟方向共五个既有不安全端点仍存在。总线偏斜报告均为 MET；DRC 没有 Error，但仍有 DSP 流水级、LUT 方程、无负载网络和 FIFO 写优先提示。报告原文均保留，未隐藏告警。

## 验证过程

1. 92 项 Python 回归通过：原始/压缩 CRC、数据和 CRC 字段损坏、协议版本一致性以及原有存储/恢复测试。
2. FPGA 仿真：6 个完整帧逐像素与输入公式一致，CRC 与独立 zlib 一致；1 个丢像素包明确无效；覆盖复位和元数据背压。
3. 本机编译实际 main.c，模拟硬件寄存器接口：验证最佳帧替换、队列/最佳帧独立引用、预览确认后不释放仍被最佳帧持有的槽、CRC 绑定及拒绝旧硬件魔数。此测试不代替 ARM 缓存/DMA 实板验证。
4. 实板同一事件 50 对 RAW/自适应传输对比，全部颜色和掩码字节、描述和 CRC 一致；中途截断后重读同一事件仍一致。
5. 正式 Station 工作线程连续接收 {c['seconds']:.3f} 秒，{c['host_captures']} 次接收、10 张缺陷证据保存；每个掩码像素、框、面积、物理来源、唯一产品号、完整入镜均通过。中心最大误差 {a['max_center_error_px']} 像素。计时窗口无新增采集间隙、无效包、队列丢失和确认错误。
6. 冻结后台模式再次验证，20 块产品中的 10 块缺陷完整保存，接收字节率相比正常预览减少 {b['received_rate_reduction_percent']:.3f}%。恢复默认仅预览及 1 GiB 上限。

## 实板传输耗时

| 输入 | RAW 请求中位数 ms | 自适应请求中位数 ms | 字节减少 % | CRC 核对中位数 ms |
|---|---:|---:|---:|---:|
{rows}

以上是 TCP 应用层及电脑处理耗时，不是线速或摄像头帧率。真实照片回放来自已有数据集，不能当作独立的新材料准确率实验。

## 实板故障注入

只在本机测试 TCP 代理中故意丢弃/修改数据，真实图像仍来自 HDMI→FPGA→DDR→网口。没有修改系统网络设置。

| 故障 | 秒 | 保存数 | 行为 |
|---|---:|---:|---|
{faults}

RAW 和压缩颜色损坏场景均验证“掩码未变、RGB 已变”，CRC 仍能拒收。损坏场景无保存、无确认、无自动重试；随后直接读取板端原事件，校验通过后才明确确认。确认回复丢失仍只重试同一确认，不再抓下一张。

## 原理和操作

详见 docs/V1.11_整帧CRC协议与原理.md：包含每像素 4 字节顺序、0xedb88320 多项式、初始和末尾取反、固定 XOR 网络、描述和网络字段布局，以及 CRC 与算法正确性的区别。

Vitis workspace 是 pynq_z2_tile_v1_53.sdk。下载 .sdk/program_ethernet.bat，根目录“启动以太网工作站.bat”打开界面。电脑 HDMI 输出固定 1280×720、60 Hz，接板 HDMI IN；板 HDMI OUT 接显示器；PROG UART USB 与直连电脑网线保持连接。界面的显示帧传输说明会标注“FPGA 整帧 CRC 已通过”，旧协议只显示未提供校验。

## 限制和下一步

CRC 检测意外损坏，不是密码学认证，不证明裂纹算法准确；本版未覆盖全部描述字段的端到端 CRC。真实掉电、拔线、长时运行及板端重启后的未决确认恢复仍需加强。此前的整数 memcpy 修复继续保留，完整中断浮点上下文及其他库函数仍需专门审计。队列有限，停止接收过久仍可能丢事件。

检测方面仍存在弱裂纹像素召回不足、跨材质误报、高速居中误差、HDMI 前一帧红框及既有 CDC 端点限制。下一步先增强描述字段与图像绑定、启动号变化的明确恢复流程，再安排更长连续运行；检测算法的下一轮优化应使用独立材料测试集，不能仅靠不断降低阈值。
'''
(R/'docs/Tile_V1.11_整帧校验与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.11

FPGA 整帧 CRC，覆盖颜色和掩码的传输损坏；Vitis 保留/转发校验值，电脑验证后才存档确认。

- Vivado：pynq_z2_tile_v1_53.xpr（本版重新实现硬件）。
- Vitis 工作区：pynq_z2_tile_v1_53.sdk；下载：.sdk/program_ethernet.bat。
- 启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.11_整帧校验与实板报告.md。
- 原理：docs/V1.11_整帧CRC协议与原理.md。
- 测试、时序、故障及哈希证据：reports/v132、DELIVERY_MANIFEST.json。
- V1.10 完整保留及 ZIP 备份；默认仅预览，1 GiB 上限。

CRC 不是检测准确率。冻结预览继续接收，停止接收过久仍可能耗尽有限队列。
''',encoding='utf-8')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.11 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:32px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.11 / 新 FPGA 硬件 · Vitis 重建 · 实板验证</p><h1>从 FPGA 到证据图，颜色也有校验</h1><section><strong>50 对完整图像一致 · 7 项故障测试通过</strong><p>故意改变 RAW / 压缩图像中的 RGB，保持掩码不变：系统拒收、不保存、不确认。原事件仍能重新读取。</p></section><section><h2>实际检查</h2><p>92 项软件回归；6 帧独立 CRC 仿真；实际固件槽所有权测试。</p><p>硬件 WNS {h['setup_wns_ns']:+.3f} ns / WHS {h['hold_whs_ns']:+.3f} ns，原时钟不变。</p><p>连续运动 60 秒保存 10 张完整证据；冻结后台节流 {b['received_rate_reduction_percent']:.2f}%，事件继续留存。</p></section><section class="warning"><h2>测试范围</h2><p>CRC 检测意外损坏，不证明算法识别准确，不是数字签名。物理掉电/拔线、独立材料盲测和既有 CDC 限制仍需后续验证。</p><p>默认仅预览，1 GiB 上限，旧工程单独保留。</p><a href="/api/benchmark">完整实测数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.11 report and validation page generated from passing evidence')
