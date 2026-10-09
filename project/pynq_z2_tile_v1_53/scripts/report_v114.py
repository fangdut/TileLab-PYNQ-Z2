from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
h=read(O/'hardware_crc_check.json');sim=read(O/'crc_sim_summary.json');n=read(O/'descriptor_native.json');df=read(O/'descriptor_fault_summary.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
assert all(x['passed'] for x in (h,sim,n,df,t,f,r,c,a,b,ui))
assert read(O/'firmware_crc_test.json')['passed'] and read(O/'native_sg/result.json')['result']=='PASS'
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 120 tests' in unit and unit.rstrip().endswith('OK')
u=(R/'reports/utilization.rpt').read_text()
resources={k:int(re.search(r'\|\s*'+re.escape(k)+r'\s*\|\s*(\d+)',u).group(1)) for k in ('Slice LUTs','Slice Registers','Block RAM Tile','DSPs')}
summary=dict(version='V1.14',passed=True,hardware=h,resources=resources,unit_tests=120,simulation=sim,native_descriptor=n,actual_descriptor_fault=df,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b)
(O/'descriptor_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {k} | {v['raw_request_ms']:.2f} | {v['compact_request_ms']:.2f} | {v['saving_percent']:.3f} |" for k,v in t['summary'].items())
doc=f'''# Tile V1.14 描述信息校验与实板报告

## 产品变化

本版保护 FPGA 生成的帧号、产品号、红框、面积和像素 CRC 等描述信息。ARM 在使用这些字段进行最佳帧判断、队列管理之前先核对描述 CRC；损坏字段被拒绝并计数。电脑界面可看到“PL 描述校验已通过”，保存的证据也记录该状态。

这解决的是传输与身份可靠性，不改变弱裂纹阈值，不把 CRC 当成检测准确率。本版完整重新构建 Vivado 硬件、导出 XSA、重建 Vitis 平台与 ELF，并进行实际 JTAG 下载。旧 V1.13 工程完整保留，另有 _baseline_backups/tile_v1_13_before_v1_14.zip；来源和哈希见 ITERATION_PLAN.json。

## FPGA、Vitis、电脑的分工

FPGA 是 720p60 实时视觉引擎，负责四方向暗谷、强弱阈值及邻域支持、区域框、产品身份和最佳帧硬件信息、像素 CRC。本版在有效像素结束后复用同一个 32 位 CRC 状态，处理 40 个描述字。40 个像素时钟约 0.539 微秒，位于帧间阶段，每像素流水线吞吐不变。原 DMA 包仍为 3686400 字节图像加 160 字节描述，没有增加传输字数。

Vitis 是 ARM 裸机数据服务：32 个 DMA 描述符、48 个 DDR 帧槽、12 个事件缓存、无损压缩、TCP 与确认。新增 CRC 只遍历 160 字节描述；ARM 不执行裂纹识别，也不重扫整幅图像计算像素 CRC。校验通过后再把硬件描述转换成网络描述，保存像素 CRC 与帧槽的关联。

电脑负责解压、整帧像素 CRC、响应头 CRC、协议语义、保存与人工复核。描述校验状态来自固件声明；电脑不重新取得原始 PL 描述进行第三次同值校验。三段检查各有范围，不能把它们称为密码学认证或对任意内部程序错误的证明。

## 原理

CRC32 初始状态为 0xffffffff，反射多项式为 0xedb88320，按小端字节处理，结束取反。描述共有 40 个 32 位字，计算时第 8 字当作零，结果写回第 8 字，避免校验值自我依赖。第 1 字含像素 CRC，因此描述身份和该像素校验值一起受检查。魔数升级为 0x54465336，旧硬件描述明确拒绝。

固件先检验魔数、描述 CRC、长度和无效标记，再递增有效帧计数和执行最佳帧逻辑。网络帧标志 bit3 表示 PL 描述校验通过；新固件帧缺少此位时电脑拒收。RAW 标志 15、RLE 标志 271；状态响应仍为 5。详细字段及状态机见 docs/V1.14_PL描述校验原理.md。

## 综合、实现与开销

仍使用 74.25 MHz 像素、100 MHz AXI/DMA、200 MHz HDMI 参考时钟。全局 WNS {h['setup_wns_ns']:+.3f} ns，WHS {h['hold_whs_ns']:+.3f} ns；CRC 输入最差建立余量 {h['crc_setup_slack_ns']:+.3f} ns。实现网表检查有 32 个共享 CRC 状态寄存器和 6 个描述索引寄存器。

| 资源 | V1.11 基线 | V1.14 实现 |
|---|---:|---:|
| LUT | 16954 | {resources['Slice LUTs']} |
| FF | 28356 | {resources['Slice Registers']} |
| BRAM tile | 58 | {resources['Block RAM Tile']} |
| DSP | 2 | {resources['DSPs']} |

模块级单独综合显示采集模块从 920 LUT/2274 FF 变为 1486 LUT/2315 FF，增加 566 LUT/41 FF，没有增加 BRAM。较多 LUT 用于描述数组的第二套动态选择逻辑；下一小版可尝试合并读取索引，实际收益必须重新实现测量。全工程资源以上表为准，不把模块数字直接当作全局差值。

DRC 没有 Error，仍有 DSP 流水级、工具 IP 的 LUT 方程、无负载网络与 FIFO 提示。两组 HDMI 时钟之间仍报告 5 个既有 CDC 不安全端点，不能用正时序余量掩盖；本版没有引入新的跨时钟数据路径。总线偏斜检查通过。完整原报告保留在 reports。

首次网表复核失败来自检查脚本：综合器把若干 MUXF7 组合选择单元也命名为 frame_crc_reg 前缀，单凭名称会误计为寄存器。保留原始单元清单，改为同时筛选 FD* 触发器原语后重跑，仍严格要求 32 个 CRC 位和 6 个索引位；没有为通过检查而放宽时序要求或修改硬件。

## 分层测试

1. 120 项 Python 回归通过，覆盖新旧协议、三段校验标志、状态响应、存储、恢复和既有规则。
2. RTL 仿真 7 个包：6 个完整帧逐像素核对；1 个故意丢像素帧被标为无效；独立 Python zlib 核对全部描述 CRC。覆盖复位与描述输出背压。
3. 本机编译实际 C：3000 组随机描述 CRC 与 zlib 一致，1280 个单比特损坏均在最佳帧/队列决策前拒绝。其中 32 个破坏魔数，其余 1248 个递增描述 CRC 错误。正常后继帧仍可接受。另有实际固件帧槽所有权回归。模拟 MMIO 不能替代 ARM/DMA 实板测试。
4. 实板 JTAG 故障：暂停 ARM，等待未来完整 DMA 描述，停住采集，在合法 48 槽 DDR 地址内将帧号第 0 位翻转；校验值保持原值。恢复 ARM 后，描述 CRC 错误恰好增加 1，有效后继描述继续处理。原描述和修改值也由独立 zlib 复核。
5. 故障试验故意暂停了采集，不将该窗口用于“无采集间隙”统计。完成后重新下载同一 BIT+ELF，获得新启动号并确认错误计数清零，再开展正常性能测量。

首次实板试验未加载 XSA 地址表，XSDB 在读取 PL 控制寄存器时停止，尚未进行 DDR 故障写入；清理流程已恢复运行并重新下载。补上本版 XSA 地址映射后重测，未使用强制内存访问选项。初始失败与最终通过日志均保留。Python 校验使用描述列表副本，避免独立 CRC 对照改变保存的原始证据。

## 实板传输、故障与恢复

50 对同一事件 RAW/RLE 全部字节一致，三段校验状态通过，中途断开后重读原事件保持一致。正常传输窗口描述错误没有增加，描述通过数与有效采集数一致。

| 输入 | RAW 请求中位数 ms | 自适应中位数 ms | 图像体字节减少 % |
|---|---:|---:|---:|
{rows}

耗时为 TCP 应用请求、解码及电脑校验时间，不是 HDMI 帧率，也不是以太网物理线速。不可压缩噪声仍直接回退 RAW。

9 类网络/数据故障通过，包括半包、丢 ACK 回复、像素/CRC/身份字段损坏和 30 秒持续不可恢复。3 项实际进程退出/JTAG 重新下载恢复通过，原图和人工备注保留，恢复没有额外抓图。正式浏览器“恢复待确认”也实际点击验证：状态、ACK、状态共 3 条请求，新增抓图 0，由 ui_restart_after.json 核对；pending_after.png 拍摄时已继续后续连续测试，所以会显示之后的会话采样数。JTAG 重新下载不等同于物理断电。

## 连续运动、节流与存储

连续 {c['seconds']:.3f} 秒，电脑接收 {c['host_captures']} 次，保存 {c['saved']} 张缺陷证据。逐像素掩码、框、面积、唯一产品身份、完整入镜检查通过，最大中心偏差 {a['max_center_error_px']} 像素。正常验收窗口无新增采集间隙、无效帧、队列丢失或确认错误。

冻结预览后台继续收取缺陷，实测接收字节率下降 {b['received_rate_reduction_percent']:.3f}%，10 个预期缺陷事件均保存。统计含应用层状态和 ACK，不含以太网链路头。验收后恢复真实照片连续移动、仅预览、不冻结，存档上限 1 GiB；主目录保留 24 张自动证据与 1 张 UI 重启证据，不持续自动堆积截图。

实现期间另做了一次 5 分钟旧 V1.13 基线运行，18003 个板端帧、没有新增保存图像和采集错误。该文件明确标注旧版本，不冒充 V1.14 的长时验收。

## 操作与回退

Vivado 打开 pynq_z2_tile_v1_53.xpr，Vitis workspace 为 pynq_z2_tile_v1_53.sdk。保持电脑 HDMI 720p60 输出到板 HDMI IN、板 HDMI OUT 到显示器、PROG UART USB 和电脑直连网线。运行 .sdk/program_ethernet.bat，再运行根目录“启动以太网工作站.bat”。旧版回退需成套使用旧 BIT、ELF 和工作站，不能混搭新描述魔数与旧固件。

## 下一步和边界

优先复用描述读取通路，降低 LUT 开销；随后修复完整 32 位事件计数回绕的 ACK=0 边界，并增加有限 DMA 自动恢复验证。当前默认一个接收端，12 事件队列仍可能溢出；未保存 DDR 图像不能跨板卡掉电恢复。PNG 与 SQLite 不是一个跨文件事务，失败写入可能留下未登记文件，但不会因此确认事件。

弱裂纹像素召回、跨材质误报、高速居中偏差、HDMI 前一帧红框、既有 CDC 端点、完整中断浮点上下文审计仍有改进空间。旧 USB/JTAG 取图路径的帧槽地址边界也需更新；当前主要验收路径是以太网。CRC 不能修复裂纹漏检，真实照片回放也不能代替实际工厂相机与独立材料盲测。
'''
(R/'docs/Tile_V1.14_描述校验与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.14

FPGA 描述 CRC，固件在使用帧号、产品号和红框之前核对；像素、网络响应头及 PL 描述三段保护。

- Vivado：pynq_z2_tile_v1_53.xpr，本版重新实现硬件。
- Vitis 工作区：pynq_z2_tile_v1_53.sdk；下载 program_ethernet.bat。
- 启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.14_描述校验与实板报告.md。
- 原理：docs/V1.14_PL描述校验原理.md。
- 120 项软件回归、RTL/实际 C、真实 DDR 单比特故障、50 对图像、网络与重启恢复、连续接收通过。
- V1.13 完整保留并有 ZIP；默认仅预览，1 GiB 上限。

CRC 不是检测准确率，也不是密码学认证；完整报告列出已知限制。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.14 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.14 / 新 FPGA 硬件 · 描述 CRC</p><h1>先核对帧与产品身份，再接收证据</h1><section><strong>真实 DDR 单比特损坏已拦截</strong><p>JTAG 修改一个未来完整帧的描述字；ARM 在最佳帧和队列决策前拒绝，后继正常帧继续处理。故障后重新下载干净版本再测性能。</p></section><section><h2>分层验证</h2><p>120 项软件回归；3000 组 C CRC；1280 个描述单比特故障；RTL 独立 zlib 对照；50 对实板图像一致。</p><p>9 类网络故障、3 项实际重启、真实 UI 恢复通过。连续运动保存 10 张完整证据，最大中心偏差 {a['max_center_error_px']} 像素。</p><p>WNS {h['setup_wns_ns']:+.3f} ns / WHS {h['hold_whs_ns']:+.3f} ns；冻结后台接收节流 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>仍需改进</h2><p>CRC 不代表算法准确率。物理掉电、工厂相机、独立材质盲测、既有 CDC 与完整计数回绕仍有边界。</p><p>默认仅预览，1 GiB 上限。</p><a href="/api/benchmark">完整实测数据 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.14 report generated from completed passing evidence')
