"""Generate the report only from completed hardware and board-test evidence."""
from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
def read(name):return json.loads((R/name).read_text(encoding='utf-8-sig'))
board=read('reports/v132/real_board/summary.json');m=read('reports/v132/build_metrics.json')
mode=read('reports/v132/mode_boundary.json');motion=read('reports/v132/motion_evidence_audit.json')
old=read('reports/weak_crack/exploration.json')['summary']['baseline']
cross=read('reports/weak_crack/cross_domain.json')['summary']['roof_ceramic']
assert board['passed'] and mode['passed'] and all(x['functional_pass'] for x in motion.values())
assert 'Ran 53 tests' in (R/'reports/weak_crack/host_tests.log').read_text(encoding='utf-8-sig')
recall=board['pixel_recall']*100;precision=board['pixel_precision']*100;old_recall=old['recall']*100
table='\n'.join(f"| {name} | {v['events']} | {v['full_events']} | {v['duplicate_physical_products']} | {v['normal_events']} | {v['center_max_error_px']} |" for name,v in motion.items())
doc=f'''# Tile V1.6 弱裂纹增强与实板验证报告

工程：D:/Vivado/pynq_z2_tile_v1_53。回退基线：D:/Vivado/pynq_z2_tile_v1_5。旧版源代码及配套硬件产物保留；本版单独构建，Vitis workspace 为 pynq_z2_tile_v1_53.sdk。

## 本次完成了什么

V1.6 在原来的四方向暗谷检测后，增加了双阈值和两级邻域支持。弱响应只有受到周围候选像素支持才补入，避免直接降低全图阈值造成大量纹理误报。识别运算仍全部在 FPGA，Vitis/ARM 增加的只是算法开关请求与瓷砖间隙提交，电脑端负责参数、显示和证据存储。

已完成独立工程、RTL 仿真、Vivado 综合布局布线及 BIT/XSA 导出、Vitis 构建、实际 JTAG 下载、同一产品内参数保持验证、50 张实际 HDMI 照片验证、连续运动与物理产品身份审计。界面提供增强模式和原规则对照，可以不重新烧录就切换。

## 算法原理：为什么不直接降低阈值

输入 RGB 先转为定点灰度：Y=(77R+150G+29B)>>8。对水平、竖直和两条对角线，比较中心与两侧距离 8 像素的邻居：

S(p)=max(0, max_d(min(Y(p−8d),Y(p+8d)))−Y(p))。

中心相对两侧更暗时，S 较大。V1.5 仅保留 S>T 的点；对当前 HDMI 瓷砖图，T=89。这能抑制正常纹理，但同一裂纹上较浅的部分也容易丢失。

V1.6 使用高阈值 TH=89，低阈值 TL=ceil(TH/2)=45。首先得到强候选 H0=[S>TH] 和弱候选 W=[S>TL]，都限制在 ROI 内。然后重复两级：

Ni(p)=sum(H(i−1)(q), q 属于 p 周围的 3×3 窗口)

Hi(p)=H(i−1)(p) OR (W(p) AND Ni(p)>=3)，i=1,2。

直观理解：强点先保留；弱点周围至少有 3 个已确认点才补入。两级最多延伸两步，不会无界地沿花纹传播。窗口计数包含中心位置；待补入弱点原本未确认时，中心自身贡献为 0。判断均为严格大于阈值，奇数阈值的一半向上取整，避免模型与 HDL 边界不一致。

这借鉴了双阈值以强响应支持弱响应的思路，参见 [OpenCV 的滞后阈值说明](https://docs.opencv.org/4.10.0/da/d22/tutorial_py_canny.html)。本项目使用自己的暗谷特征、有限两级与至少三点支持，既不是完整 Canny，也不是 YOLO 或神经网络。

最初直接按八邻域补全时，230 张正常标定图有 5 张新增报警。增加至少三点支持后，这批标定图恢复为 0/230 报警。这个架构选择使用了历史回归信息，因此以下数据不能当作新的独立盲测。

## 实际检测效果

| 指标 | V1.5 | V1.6 |
|---|---:|---:|
| 历史裂纹照片报警 | 16/17 | {board['counts']['crack']['alarms']}/17 |
| 历史正常照片报警 | 0/33 | {board['counts']['good']['alarms']}/33 |
| 裂纹像素召回率 | {old_recall:.2f}% | {recall:.2f}% |
| 裂纹图上的候选像素精确率 | {old['precision']*100:.2f}% | {precision:.2f}% |
| 本版输出逐像素及区域匹配参考规则 | — | {board['pixel_exact']}/50 |

召回率=TP/(TP+FN)：标注的裂纹像素中找回了多少。精确率=TP/(TP+FP)：算法挑出的像素中有多少落在标注裂纹上。它们描述候选掩码，而不是整块瓷砖的合格判定。50/50 一致说明硬件实现正确执行规则，并不说明规则无漏检。

本版仍只提取部分裂纹。特别是 real_005：旧规则有 30 个候选像素，未达到区域报警门槛；新规则补到约 50 个，能报警，但红框仍只覆盖宽裂纹顶端局部，不能表述为完整定位了整条裂纹。没有强种子的孤立弱裂纹、比当前邻域尺度更宽的裂纹、反光和与纹理混淆的裂纹仍有风险。

## 跨材质结果与模式回退

固定原始图像高阈值 105，对已有屋面瓦照片只读复测，规则冻结后不再用这批结果调参：

| 屋面瓦标签 | 样本数 | V1.5 报警 | V1.6 报警 |
|---|---:|---:|---:|
| 正常 | 800 | {cross['normal']['old_alarms']} | {cross['normal']['new_alarms']} |
| 缺陷 | 800 | {cross['defective']['old_alarms']} | {cross['defective']['new_alarms']} |

新增弱响应同时放大了跨材料纹理误报。这一结果是本版的明确适用范围限制，不能只展示检出上升。屋面瓦缺陷标签还含形变等类型，不能把上表当作纯裂纹准确率。原始照片参数 105 与当前电脑实际 HDMI 图像参数 89 属于不同颜色链路，不应混用。

因此菜单保留“原检测规则对照”。切换只在瓷砖间隙生效，并在每张证据中记录实际配置 bit24、实际高/低阈值和算法标识。该开关不是材质自动识别；更换材质、相机、照明、图像尺度仍需要独立标定和检验。

## FPGA、Vitis 和电脑分别改了什么

FPGA 改动为 rtl/raster_morph.v 与 rtl/video_bypass.v：窗口中增加弱候选位，计算九点支持数，以配置 bit24 选择增强。复用原来两级形态学处理窗口与侧带延迟，保持一拍一像素吞吐以及原来的像素对齐延迟；未提高时钟。

Vitis 改动为 ethernet_sources/main.c、network.c、event_queue.h：固件版本 0x00010600；采集请求的第 4 个字选择增强或基线；元数据 61/62 记录待应用/已应用的关闭增强标志。ARM 仅提交 FPGA 参数，没有遍历图像实现裂纹检测。原有 SG32、48 个 DDR 槽、12 条待确认队列和所有权管理保留。

电脑端新增增强/原规则两种材料参数，依据采集帧真实配置归属证据，显示实际高/低阈值。仍默认仅预览、不自动存图，存档上限 1 GiB；正式测试只留必要的有限证据，没有复制旧版海量存档和屋面瓦原图。

## 时序与资源

像素 74.25 MHz，DMA/DDR 接口 100 MHz，HDMI 参考 200 MHz。最终 WNS={m['wns_ns']:+.3f} ns，WHS={m['whs_ns']:+.3f} ns，TNS={m['tns_ns']:.3f} ns。

LUT {int(m['resources']['lut'])}/53,200；FF {int(m['resources']['ff'])}/106,400；BRAM {m['resources']['bram36']:g}/140；DSP {m['resources']['dsp']:g}/220。相对 V1.5 仅增加 16 LUT、6 FF，BRAM 与 DSP 不增加。总线偏斜检查 {m['bus_skew_constraints_checked']} 项通过。

遗留 HDMI IP 仍有 {m['legacy_hdmi_cdc_unsafe_endpoints']} 个不安全跨时钟端点，本次没有把它们消除。时序满足不意味着整个系统已具备工业级跨时钟可靠性。

## 验证清单

- RTL：10,368 个像素，覆盖随机邻域、孤立强种子、没有强种子的弱区域、有限传播路径和像素侧带对齐。
- 电脑软件：53 项单元回归，包括存储限额、确认语义、协议帧、算法开关传输与证据归属。
- 实板：50 张带 HDMI 身份条码的照片，核对来源编号、掩码、区域框和区域面积，防止读取旧画面。
- 实板模式切换：同一静态产品内保持旧算法，离站后才改变；基线掩码、增强掩码均与参考逐像素一致。
- 连续运动：真实照片合成场景 120 秒、合成高速场景 60 秒；输入持续移动，不在检测中心停车。

| 运动场景 | 留图数 | 完整留图 | 重复物理产品 | 正常产品误留 | 最大居中偏差/px |
|---|---:|---:|---:|---:|---:|
{table}

运动功能审计均通过。真实照片场景最差居中偏差 10 像素，合成高速场景为 40 像素，后者没有达到 32 像素目标；审计脚本因此返回非零并保留失败日志，不能用完整留图通过来掩盖居中指标失败。本轮修改针对弱响应，未重写 V1.5 选帧器。连续运动输入来自真实照片的平移或合成纹理，不是工厂相机视频。

两个计时窗口的板端原始采集均约 60 fps；真实场景电脑取图 1022 次/120.234 秒（约 8.5 fps），高速场景 568 次/60.313 秒（约 9.4 fps）。电脑预览率不等于 FPGA 处理率。分别完成 40/80 个产品、保存 20/40 条缺陷证据，采集间隙、损坏帧、队列丢弃计数均未增加。运行前后的网络诊断有相同的历史 timeout 计数 1，计时窗口内没有新增，不能表述为整次会话从未发生网络超时。

用户已明确反馈：“持续移动、画面稳定，有红框”，记录在 reports/v132/display_confirmation.json。静态照片测试首次曾因 Windows 原子替换播放器状态文件时的短暂读锁中断，已加入有界重试并完整重跑通过；首次失败日志保留，没有将不完整测试计入通过数。

## 操作与回退

电脑 HDMI→板 HDMI IN；板 HDMI OUT→显示器；USB→PROG UART；网线开发板直连电脑。输入固定 1280×720、60 Hz。必要时先运行 .sdk/program_ethernet.bat，再运行“启动以太网工作站.bat”。

材料选择“本机 HDMI 瓷砖 · 弱裂纹增强”。测试输入可选“旧版漏检的裂纹样本”查看 real_005，也可选真实照片连续流水线。为了对照，先切空传送带，选择原检测规则，再切回同一照片。动态输入下则等待瓷砖自然离站即可。不要把静态图一直停留时的待应用参数误认为设置失效。

电脑界面使用该张图对应的 FPGA 坐标；HDMI 直通仍可能使用上一帧统计坐标，存在运动框滞后限制。程序采集与显示器目视反馈应分别记录。

要完整回到 V1.5，停止 V1.6 工作站和输入播放器，运行旧目录自己的 program_ethernet.bat 与启动脚本。烧录使用本版匹配 BIT/XSA/ELF，不能混用。JTAG 配置断电丢失，未写 Flash。

## 后续最值得做的事

第一，增加多尺度暗线特征，兼顾细线与宽裂纹；结合方向连续性或受限的更长连接，改善完全无强种子和长断裂段。第二，收集未参与开发的实体瓷砖或生产批次做盲测，特别评估反光、花纹、真实运动模糊；不能用重复平移同一张图增加“样本数”。第三，基于实测瓶颈减少传输负载，完善断网、断电、持久化启动和留存策略。提频不能弥补规则的语义判断能力，也不能突破千兆链路对全分辨率 60fps 原始流的带宽限制。

核心结论：当前纹理瓷砖的弱响应得到可量化改善，且增强逻辑确实运行于 FPGA；完整裂纹覆盖、跨材质泛化和生产可靠性仍有明确差距。
'''
(R/'docs/Tile_V1.6_弱裂纹增强报告.md').write_text(doc,encoding='utf-8')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.6 · 弱裂纹验证</title><style>body{{margin:0;background:#eef4f5;color:#173e47;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1080px;margin:auto;padding:32px}}a{{color:#087d80}}h1{{font-size:32px;margin:12px 0}}section{{background:white;padding:26px;border:1px solid #d9e5e8;border-radius:18px;margin:22px 0}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}strong{{font-size:28px;color:#087d80}}.warning{{border-left:5px solid #cb713a;background:#fff4e9}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #dde7e8}}img{{width:100%;height:auto}}small{{color:#627b83}}@media(max-width:650px){{.metrics{{grid-template-columns:1fr}}main{{padding:16px}}}}</style><main><a href="/">← 返回检测工作台</a><small>　实板 V1.6 / 历史回归</small><h1>补全弱响应，保留可核验的边界</h1><p>识别在 FPGA，ARM 传输数据。以下数字来自实际 HDMI 输入与本次板端掩码，架构使用过历史样本开发，不能当作独立工业准确率。</p><section class="metrics"><div>裂纹照片报警<br><strong>16 → 17 / 17</strong></div><div>裂纹像素召回率<br><strong>{old_recall:.2f}% → {recall:.2f}%</strong></div><div>正常照片误报<br><strong>0 / 33</strong></div></section><section><h2>如何补全</h2><p>高阈值 89 提供强种子；低阈值 45 保留可疑弱点。弱点周围至少有 3 个已确认候选才能补入，连续两级。复用原有 FPGA 窗口，保持 720p60。</p><p>50/50 掩码与区域结果逐像素匹配；模式切换在产品离站后生效。原检测规则可在材料菜单中选择，无须重烧。</p></section><section class="warning"><h2>不能忽略的代价</h2><p>跨材质屋面瓦正常误报由 19/800 增至 107/800。增强模式适用于本次验证的纹理瓷砖与成像条件，不是通用材质配置。</p><p>像素召回率仍只有 {recall:.2f}%。原漏报样本虽然现在报警，红框仍只覆盖宽裂纹的一小段；不能说整条裂纹已经完整识别。</p></section><section><h2>看同一张实采图上的差异</h2><img src="/weak-comparison.png" alt="原图、旧规则和弱裂纹增强的候选像素及红框对比"><p><small>右列掩码与本次实板一致；左侧旧规则对照在相同实采 RGB 上计算。输入来自 MVTec AD tile。</small></p></section><section><h2>本次硬件验证</h2><p>WNS {m['wns_ns']:+.3f} ns；53 项软件测试通过；10,368 像素 RTL 验证通过。真实照片运动和合成高速运动均核对了产品身份、完整截图与同帧掩码。</p><p>遗留 HDMI 跨时钟端点与高速居中限制仍单列记录。本页不表示已经通过工厂生产验收。</p></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.6 report and evidence page generated from completed board tests')
