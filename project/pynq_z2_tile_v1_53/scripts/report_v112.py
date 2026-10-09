"""Build the V1.12 report from this release's completed test artifacts."""
from pathlib import Path
import json

R = Path(__file__).resolve().parents[1]
O = R / 'reports/v132'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
t = read(O/'transport_comparison.json')
f = read(O/'recovery/summary.json')
c = read(O/'station_continuous.json')
a = read(O/'station_identity_audit.json')
b = read(O/'background_summary.json')
n = read(O/'header_crc_native.json')
assert all(x['passed'] for x in (t,f,c,a,b,n))
unit = (O/'host_tests_final.log').read_text(encoding='utf-8-sig')
assert 'Ran 102 tests' in unit and unit.rstrip().endswith('OK')
inherited = read(R.parent/'pynq_z2_tile_v1_11/DELIVERY_MANIFEST.json')
summary = dict(version='V1.12',passed=True,unit_tests=102,header_native=n,
    hardware_inherited_from='V1.11',hardware=inherited['validation']['hardware'],
    transport=t['summary'],faults=f,
    station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b)
(O/'header_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {s['raw_request_ms']:.2f} | {s['compact_request_ms']:.2f} | {s['saving_percent']:.3f} | {s['crc_ms']:.3f} |" for name,s in t['summary'].items())
faults='\n'.join(f"| {x['name']} | {x['seconds']:.3f} | {x['saved']} | {'恢复成功' if x['recovered'] else '拒收/停止'} |" for x in f['cases'])
doc=f'''# Tile V1.12 身份与响应头校验实板报告

## 这版解决的问题

V1.11 已经校验整帧颜色和掩码，但一张图片还对应帧号、瓷砖编号、红框坐标、参数和板卡启动号。如果网络中的这些字段发生意外改变，只有像素 CRC 仍不能发现。本版在 Vitis 到电脑的每条响应中新增响应头 CRC，电脑先核对身份和描述，再接收图像、检查 FPGA 像素 CRC、保存和确认。

本版是固件和电脑软件迭代。FPGA BIT、XSA、LTX 与已经实板验收的 V1.11 完全相同，未重新声称完成硬件实现；新 Vitis ELF 真正重新编译并通过 JTAG 下载。下载记录和文件哈希见 reports/programmed_v132.json。旧 V1.11 文件夹完整保留，另有 _baseline_backups/tile_v1_11_before_v1_12.zip 源码和下载文件备份；ZIP 不包含海量运行归档，旧文件夹保留原证据。

## 三部分各自完成什么

FPGA 仍是实时检测引擎：720p60 HDMI 输入、方向暗谷响应、双阈值弱裂纹支持、区域框、产品跟踪、最佳截图选择、整帧像素 CRC。主要视觉运算保持在 FPGA。

Vitis 是 Cortex-A9 裸机数据服务：DMA 槽管理、事件队列、无损压缩、以太网发送和确认。本版只对 272 字节短响应头计算 CRC，不让 ARM 重新扫描 3,686,400 字节图像计算像素 CRC，更不在 ARM 做裂纹检测。原有 32 个 DMA 描述符、48 个帧槽和 12 个事件容量保持不变。

电脑工作站完成解压、两层校验、持久保存与人工复核。界面分别标注“FPGA 整帧 CRC”和“帧号/坐标校验”；历史协议明确显示未提供响应头校验。被冻结的预览仍可后台接收，保存行为仍由存储模式决定。

## 协议和原理

原有 68 个 32 位小端字共 272 字节不改变位置，末尾追加 4 字节 CRC，新的响应头共 276 字节。RAW 帧 flags=7、压缩帧 flags=263、状态/确认/配置 flags=5；固件版本 0x00010c00。追加开销只有 4 字节，真实照片的压缩收益保持。

CRC 初值 0xffffffff，反射多项式 0xedb88320，完成后取反。每个 32 位小端字先与当前状态异或，再执行 32 次右移及条件异或。像素 CRC 由 FPGA 流水线产生，覆盖颜色与掩码；响应头 CRC 由 Vitis 产生，覆盖版本、身份、长度、坐标和像素 CRC 字段。两个校验对应不同边界，详细布局、公式及新旧协议兼容规则见 docs/V1.12_响应头校验原理.md。

## 逐步验证

1. 最终 102 项 Python 回归通过，包含 RAW/RLE、状态/确认/配置、版本/标志不一致、截断以及不同字段受损。初次新测试把压缩响应配给未请求压缩的客户端，生产端正确拒绝；修正测试请求标志后全部通过，初始日志也保留，没有修改生产检查去迁就测试。
2. 实际 C 响应头函数本机编译，与独立 zlib 比较 3000 组输入全部相符。本机测试不冒充 ARM 实板执行，ARM 集成另由下述网络测试验证。
3. 真实开发板输出 50 对同一事件 RAW/自适应数据，逐字节完全一致且两层 CRC 均通过。中途截断后重读同一事件也通过；观察到过一次网络重传/重连并已恢复，不能声称网络从未重试。
4. 正式工作线程持续接收 {c['seconds']:.3f} 秒，完成 {c['host_captures']} 次电脑接收，保存 {c['saved']} 张缺陷证据。全部保存图像的掩码、面积、框、物理来源、唯一产品号、完整入镜检查通过，最大居中误差 {a['max_center_error_px']} 像素。测试窗口内没有新增板端采集间隙、无效包、队列丢失或确认错误。
5. 正常预览和冻结后台接收 A/B 实板测试通过，冻结后台接收字节率降低 {b['received_rate_reduction_percent']:.3f}%。这是 TCP 应用层接收字节率，包含状态和确认，不包括以太网/TCP 头，不等同于算法速度提高。

## 实板传输中位数

| 输入 | RAW 请求 ms | 自适应请求 ms | 图像体减少 % | 像素 CRC ms |
|---|---:|---:|---:|---:|
{rows}

输入包含真实瓷砖照片回放、合成场景、空白及噪声。对难压缩噪声仍自动回退 RAW；网络传输/电脑接收约几十毫秒，不意味着 HDMI 帧率低于 60。

## 实板故障注入

测试代理只作用于本机测试连接。输入和实际待保存事件均来自 HDMI→FPGA→DDR→以太网，不是伪造板端图像。

| 情形 | 耗时秒 | 保存数 | 结果 |
|---|---:|---:|---|
{faults}

帧号、产品号、像素 CRC 字段和 RAW/RLE 颜色被故意破坏时，电脑都拒收，不保存、不确认、不当成普通断网自动重试。原事件仍能直接重读并校验后确认。短时断网、截断和确认回复丢失可以在有限时间内恢复；30 秒持续故障明确停止。

另有软件工作线程测试验证损坏确认回复后，已保存的图和待确认身份保留，恢复只确认原事件；这是软件控制故障测试，不声称做了物理拔线或真实损坏 ACK 的完整 UI 恢复测试。

## 操作和保存空间

工程是 pynq_z2_tile_v1_53.xpr，Vitis 工作区是 pynq_z2_tile_v1_53.sdk。用 .sdk/program_ethernet.bat 下载，根目录“启动以太网工作站.bat”启动。电脑 HDMI 输出 1280×720、60 Hz 接 HDMI IN，板 HDMI OUT 接显示器；PROG UART USB 及直连电脑的网线保持连接。

验收后恢复真实照片连续移动、仅预览、1 GiB 保存上限。仅预览不自动不断写硬盘；本次有界测试保存少量可追溯证据，不删除旧工程和原始测试集。

## 已知不足与下一步

响应头 CRC 只能保护 Vitis 产生之后的传输，尚未保护 PL→DMA→ARM 中的全部描述字段。CRC 是偶发错误检测，不是密码学认证，也不证明裂纹算法准确。板卡重启时未决确认需要明确处理；长时运行、物理拔线、断电仍需测试。队列只有 12 个事件，长时停止接收仍可能溢出。

硬件继承 V1.11：WNS +0.170 ns、WHS +0.011 ns，LUT 16954、FF 28356、BRAM 58、DSP 2。像素/AXI/参考时钟保持 74.25/100/200 MHz。既有 HDMI CDC 不安全端点和很小的 hold 余量没有被本版消除。完整中断浮点上下文与其他库函数仍需审计。

检测性能也未被协议改动改善：跨材料误报、无强种子的弱裂纹、高速截图居中偏差、HDMI 使用前一帧框仍存在。真实照片连续回放不等于工厂真实运动相机测试。下一版优先完善启动号变化与未决确认恢复，随后再考虑 PL 描述保护和更长连续运行。
'''
(R/'docs/Tile_V1.12_身份校验与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.12

FPGA 像素 CRC + Vitis 响应头 CRC：图像和帧号、产品号、坐标均校验后才保存/确认。

- Vivado：pynq_z2_tile_v1_53.xpr；硬件继承已验收的 V1.11。
- Vitis 工作区：pynq_z2_tile_v1_53.sdk；下载 .sdk/program_ethernet.bat。
- 启动：根目录“启动以太网工作站.bat”。
- 实板报告：docs/Tile_V1.12_身份校验与实板报告.md。
- 原理：docs/V1.12_响应头校验原理.md。
- 测试证据：reports/v132；交付哈希：DELIVERY_MANIFEST.json。
- V1.11 完整保留并另有源码/下载文件 ZIP；默认仅预览，1 GiB 上限。

本版 102 项软件回归、3000 组实际 C 校验对照、50 对实板逐字节比较和 9 项故障测试通过。CRC 不等于算法准确率，PL 到 ARM 的描述字段尚未有独立校验。
''',encoding='utf-8')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.12 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:30px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.12 / 新固件实板验证 · FPGA 继承 V1.11</p><h1>图像与身份，分两层检查</h1><section><strong>50 对图像一致 · 9 项故障测试通过</strong><p>故意改坏帧号、瓷砖编号、校验字段或 RGB：拒收、不保存、不确认，板端原事件仍可重读。</p></section><section><h2>本版实测</h2><p>102 项软件回归；3000 组实际 C 校验函数与 zlib 对照。</p><p>连续运动 {c['seconds']:.1f} 秒保存 {c['saved']} 张完整证据，身份、掩码、面积、框全部一致。</p><p>冻结后台接收字节率降低 {b['received_rate_reduction_percent']:.2f}%，事件继续留存。</p></section><section class="warning"><h2>边界仍需说明</h2><p>响应头 CRC 从 Vitis 开始，PL 到 ARM 的描述字段尚未独立校验。CRC 不是签名，也不证明算法准确。物理掉电/拔线、长时运行及既有 CDC 限制仍待验证。</p><p>默认仅预览，1 GiB 上限，旧工程独立保留。</p><a href="/api/benchmark">完整实测数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.12 report and validation page generated from passing evidence')
