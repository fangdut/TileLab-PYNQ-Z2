from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
o=read(O/'capture_optimization.json');random=read(O/'random_equivalence.json');h=read(O/'hardware_crc_check.json');change=read(O/'change_audit.json')
sim=read(O/'crc_sim_summary.json');n=read(O/'descriptor_native.json');df=read(O/'descriptor_fault_summary.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json');soak=read(O/'baseline_v114_soak.json')
assert all(x['passed'] for x in (o,random,h,sim,n,df,t,f,r,c,a,b,ui,soak,change))
assert read(O/'firmware_crc_test.json')['passed'] and read(O/'native_sg/result.json')['result']=='PASS'
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 120 tests' in unit and unit.rstrip().endswith('OK')
u=(R/'reports/utilization.rpt').read_text()
resources={k:int(re.search(r'\|\s*'+re.escape(k)+r'\*?\s*\|\s*(\d+)',u).group(1)) for k in ('Slice LUTs','Slice Registers','Block RAM Tile','DSPs')}
assert resources['Slice LUTs']<17503,'No implemented LUT reduction: do not label release as successful area optimization'
baseline_soak=dict(passed=True,release_tested=soak['release_tested'],seconds=soak['seconds'],frames=soak['after']['board_stats']['frames']-soak['before']['board_stats']['frames'],new_images=soak['new_images'],new_records=soak['new_records'],scope=soak['scope'])
summary=dict(version='V1.15',passed=True,optimization=o,random_equivalence=random,hardware=h,resources=resources,implemented_lut_saved=17503-resources['Slice LUTs'],unit_tests=120,simulation=sim,native_descriptor=n,actual_descriptor_fault=df,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,prior_release_soak=baseline_soak)
(O/'shared_port_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {k} | {v['raw_request_ms']:.2f} | {v['compact_request_ms']:.2f} | {v['saving_percent']:.3f} |" for k,v in t['summary'].items())
rc=random['coverage']
doc=f'''# Tile V1.15 共享描述读取通路与实板报告

## 本版完成的优化

V1.14 的描述 CRC 和描述输出分别使用独立数组读取索引，虽然两个阶段互斥，综合器仍需要较多选择逻辑。V1.15 让它们共用一个索引和读取通路，保留原来的 CRC、帧身份、像素、红框和时序行为，减少 FPGA 资源。

本版重新完成 Vivado 综合、布局布线、生成 BIT/XSA/LTX，依据新 XSA 重建 Vitis 平台与 ELF，实际下载并测试。V1.14 原工程完整保留，另有 _baseline_backups/tile_v1_14_before_v1_15.zip；备份哈希和逐文件检查见清单。

## 各部分的产品与边界

FPGA 是 HDMI 720p60 视觉与证据引擎：弱裂纹候选、邻域支持、区域框、产品身份与帧质量信息、像素 CRC、描述 CRC。Vitis 是裸机 DMA/DDR/以太网服务，管理帧槽、最佳帧引用、事件缓存、无损压缩、确认及 160 字节描述校验。电脑是预览、接收校验、证据存储与人工复核工作站。

视觉算法继续在 FPGA。本版不修改检测阈值、区域算法、帧槽数、压缩格式或网络包长度；Vitis 重新编译为版本 0x00010f00。资源减少不能宣称为弱裂纹准确率、网速或工厂每秒产品数提高。

## 资源测量

相同工具、器件和 OOC 综合设置下，采集模块从 {o['baseline']['Slice LUTs']} LUT/{o['baseline']['Slice Registers']} FF 降到 {o['optimized']['Slice LUTs']} LUT/{o['optimized']['Slice Registers']} FF，减少 {o['lut_saved']} LUT（{o['lut_reduction_percent']:.2f}%）和 {o['ff_saved']} FF，没有新增 BRAM/DSP。此百分比只针对采集模块。

| 全工程资源 | V1.14 实现 | V1.15 实现 |
|---|---:|---:|
| LUT | 17503 | {resources['Slice LUTs']} |
| FF | 28397 | {resources['Slice Registers']} |
| BRAM tile | 58 | {resources['Block RAM Tile']} |
| DSP | 2 | {resources['DSPs']} |

全工程实际减少 {17503-resources['Slice LUTs']} LUT。仍为 74.25 MHz 像素、100 MHz AXI/DMA、200 MHz参考时钟。最终 WNS {h['setup_wns_ns']:+.3f} ns、WHS {h['hold_whs_ns']:+.3f} ns，CRC 输入建立余量 {h['crc_setup_slack_ns']:+.3f} ns。网表核查共享索引存在，单独 crc_index 已移除。

OOC 报告的 “Slice LUTs*” 带脚注星号，首次汇总解析器没有处理星号而失败，已修正解析后使用原始综合报告重算；没有调整测量数字或重跑硬件来制造收益。最终资源、时序、DRC、CDC 和总线偏斜报告都保留原文。既有 CDC 等限制仍需后续处理，不以正时序余量代替 CDC 审查。

## 原理

寄存器数组的动态读取会综合成多路选择器，两个不同读取索引可能产生两套选择逻辑。CRC 阶段与 AXIS 描述输出阶段互斥，因此可以分时复用一套读取通路。

CRC 阶段每个周期推进索引；输出阶段仅在输出寄存器空闲或下游接收时推进。CRC 处理完第 39 字的时钟沿，同时写入第 8 字校验值、清零索引、转入输出状态。非阻塞赋值保证这一沿的 CRC 仍使用原来的第 39 字。40 个 CRC 周期仍约 0.539 微秒，不额外增加每像素周期或描述字数。

详细状态图、公式、术语和答辩要点见 docs/V1.15_共享描述读取通路原理.md。

## 先验证等价，再测实板

固定用例 {o['equivalent_cycles']} 周期逐周期比较新旧输出，包括完整帧、丢像素、产品开始/结束和描述背压。参考 RTL 来自 V1.14 已验收清单，先核对 SHA256。6 个有效帧与独立输入公式逐像素一致；7 个描述 CRC 与独立 zlib 一致；故意丢像素的一帧明确无效。

额外随机用例使用固定种子 0xcafe1547，比较 {rc['cycles']} 周期，产生 {rc['packets']} 个完整包，覆盖 {rc['stalls']} 次背压、{rc['pixel_resets']} 次像素中途复位、{rc['crc_resets']} 次 CRC 中途复位、{rc['trailer_resets']} 次输出中途复位和 {rc['disabled']} 个禁用输入周期。所有可观察输出与旧版一致，不生成海量随机图像文件。这是有限仿真，不是形式化证明，也不表示真实 HDMI 丢失后的 DMA 自动恢复已经解决。

120 项 Python 回归通过。实际 C 的 3000 个随机描述 CRC、1280 个单比特错误以及帧槽引用/队列所有权测试通过。随后在新 BIT+ELF 上实际通过 JTAG 修改一个未来完整 DMA 描述的帧号单比特，固件拒绝该描述，后继正常帧继续处理。故障后重新下载同一版本，清除故意暂停造成的测试状态，再测正常性能。

## 新版实板结果

50 对同一事件 RAW/压缩图像全部字节一致，像素、响应头及 PL 描述三段校验通过；半包断开后仍能重读原事件。9 类网络/数据故障、3 类实际异常退出/JTAG 重载以及正式界面待确认恢复均通过。恢复先核对启动号与原证据，未额外抓图，原图和人工备注保留。

| 输入 | RAW 请求中位数 ms | 自适应中位数 ms | 图像体字节减少 % |
|---|---:|---:|---:|
{rows}

这里是应用层请求、解码和电脑校验耗时，不是 HDMI 帧率。不可压缩输入保留 RAW 回退，不承诺每种内容压缩都更快。

连续移动测试 {c['seconds']:.3f} 秒，接收 {c['host_captures']} 次，保存 {c['saved']} 张缺陷证据。掩码逐像素、区域框、面积、物理产品身份与完整入镜核对通过，最大居中误差 {a['max_center_error_px']} 像素。正常验收窗口未增加采集间隙、无效帧、描述校验错误、队列丢失和确认错误。

冻结后台预览的接收字节率下降 {b['received_rate_reduction_percent']:.3f}%，10 个预期缺陷事件均保留。按 TCP 应用层字节计量，含状态/ACK，排除链路头。验收后仅预览、真实照片继续移动、存档上限 1 GiB；主目录保留 24 张自动证据和 1 张重启测试证据。

## 构建期间的旧版基线

V1.15 构建期间，板上 V1.14 另运行 {baseline_soak['seconds']:.3f} 秒，前 5 分钟正常预览、后 5 分钟冻结后台。共经过 {baseline_soak['frames']} 个板端帧，没有新增图像或记录，监测的间隙、无效帧、描述错误、队列丢失和确认错误未增加。它属于旧版基线，明确不冒充 V1.15 长时验证或物理相机测试。

## 使用和回退

Vivado 工程为 pynq_z2_tile_v1_53.xpr，Vitis workspace 为 pynq_z2_tile_v1_53.sdk。运行 .sdk/program_ethernet.bat 下载，根目录“启动以太网工作站.bat”启动。连接保持电脑 HDMI 720p60→板 HDMI IN→板 HDMI OUT→显示器，另接 PROG UART USB 和电脑直连网线。回退使用 V1.14 成套 BIT、ELF、工作站。

## 下一步

构建期间的只读 ELF 审计发现，V1.14 实际中断入口没有浮点上下文保存，而链接代码中仍有 VFP 指令；应用使用 hard-float 编译配置。证据和后续完成标准在 docs/V1.15_中断上下文只读审计.md。下一版优先用可复现 BSP 配置和真实中断寄存器测试补齐这一点，保留已验证的整数 memcpy。

随后处理 HDMI 信号复位后的 DMA 检测与有界恢复、有限缓存满时的明确行为、USB/JTAG 辅助取图地址界限，以及长期事件编号回绕。当前 ACK=0 和非 2 的幂队列长度在完整计数回绕时都需要专门审计，不能承诺无限期运行。

视觉方面仍需独立材料测试集衡量弱裂纹像素召回与纹理误报，不能用降低阈值替代验证。HDMI 使用前一帧坐标、高速截图居中偏差、既有 CDC、完整中断浮点上下文审计仍有改进空间。CRC 检查意外损坏，不是密码学认证，也不保证算法准确。未保存的 DDR 证据不能跨板卡掉电恢复；PNG 与 SQLite 不是跨文件事务；目前按一个接收端设计。真实照片合成运动不等于实际工厂相机。
'''
(R/'docs/Tile_V1.15_读取通路优化与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.15

共享描述 CRC/输出读取通路，减少 FPGA 选择逻辑，保持 V1.14 的校验、检测和传输行为。

- Vivado：pynq_z2_tile_v1_53.xpr，本版重新实现硬件。
- Vitis workspace：pynq_z2_tile_v1_53.sdk；下载 program_ethernet.bat。
- 启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.15_读取通路优化与实板报告.md。
- 原理：docs/V1.15_共享描述读取通路原理.md。
- 固定及随机新旧 RTL 逐周期对照、独立 CRC、120 项软件回归、实板故障、连续和后台接收通过。
- V1.14 完整保留并有 ZIP，默认仅预览，1 GiB 存档上限。

模块 LUT 优化比例不等于全工程比例。CRC 和资源优化不代表检测准确率提高。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.15 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.15 / 共享描述读取通路 · 新硬件</p><h1>保留完整校验，减少重复选路电路</h1><section><strong>采集模块 LUT 减少 {o['lut_reduction_percent']:.2f}%</strong><p>同设置 OOC：1487 → 1028 LUT；全工程实现减少 {17503-resources['Slice LUTs']} LUT。未增 BRAM/DSP，时钟和数据格式保持。</p></section><section><h2>先对照行为，再测实板</h2><p>固定 {o['equivalent_cycles']:,} 周期、随机 {rc['cycles']:,} 周期新旧输出一致，覆盖背压和中途复位。120 项软件回归通过。</p><p>真实 DDR 单比特故障已拦截；50 对实板 RAW/压缩图像一致；9 类网络故障、3 类重启和真实 UI 恢复通过。</p><p>WNS {h['setup_wns_ns']:+.3f} ns / WHS {h['hold_whs_ns']:+.3f} ns；后台接收节流 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>验证范围</h2><p>有限仿真不是形式化证明；CRC 与资源减少不是算法准确率。物理掉电、HDMI 丢失恢复、CDC、计数回绕和独立材料盲测仍需后续工作。</p><p>默认仅预览，1 GiB 上限。</p><a href="/api/benchmark">完整实测数据 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.15 report generated only after completed passing evidence')
