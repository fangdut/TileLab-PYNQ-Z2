from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
n=read(O/'health_native.json');w=read(O/'health_board/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
assert all(v['passed'] for v in (n,w,fw,t,f,r,c,a,b,ui,dc,sc)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 138 tests' in units and units.rstrip().endswith('OK')
summary=dict(version='V1.19',passed=True,firmware=fw,health_native=n,health_board=w,unit_tests=138,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,
             station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,hardware_origin='Unchanged V1.15 BIT/XSA/LTX; V1.16 IRQ, V1.17 ring positions and V1.18 ACK isolation retained')
(O/'capture_health_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
health_rows='\n'.join(f"| {v['operation']} | {v['after_fault']['capture_health']['state']} | {v['after_fault']['active']} | {v['status_bytes_per_second']:.1f} |" for v in w['cases'])
doc=f'''# Tile V1.19 采集健康监测与实板验收报告

## 本版交付什么

工作站现在分别显示网络连通与完整图像采集状态。启动未收到有效帧、DMA 无进展、持续无效数据、DMA 错误、DMA 停止均有独立状态。没有新帧且队列为空时，只轮询小状态包，避免把“视频未就绪”反复变成整帧请求超时。已排队证据照常读取、校验、确认；手动抓拍保留一次待执行意图，停止接收可取消。

本版只做观察与等待，没有自动 DMA 复位。实板故障结束由受控测试脚本恢复输入或重新下载干净正式固件。自动恢复留给下一版分阶段实现。

## 保存和构建

- 旧工程完整保留：D:/Vivado/pynq_z2_tile_v1_18。
- 本版工程：D:/Vivado/pynq_z2_tile_v1_53；Vivado 为同名 .xpr；Vitis workspace 为同名 .sdk。
- 备份：D:/Vivado/_baseline_backups/tile_v1_18_before_v1_19.zip，SHA256 e1fa7b7ae29ef5aa93702ac628ef4e5ff3eb63199c8fa76e650fcf89f6568575。
- Vivado 建立正常工程结构，BIT/XSA/LTX 与已验证 V1.15 完全相同。本版没有重新布局布线，也没有新的时序、频率或算法准确率结论。
- Vitis 完整构建平台与应用，text 129870 B、data 3476 B、bss 7435728 B；text 较 V1.18 增加 608 B，另外两项相同。ELF SHA256：{fw['elf_sha256']}。
- 实际反汇编核对中断浮点现场保护、4 KiB IRQ 栈和整数 memcpy。作者源码与 Vitis 导入源码逐项相同，队列确认逻辑与 V1.18 一致。

## 改动职责

FPGA 继续做 720p60 像素处理、弱裂纹增强、区域框、产品经过识别、最佳帧选择以及像素和描述校验。ARM 新增时间戳与 DMA 状态采样，依旧负责 DDR 槽管理、无损传输和确认；没有增加 ARM 图像识别。电脑负责状态呈现、完整性验证、留图和人工复核。

capture_health.h 保存最近 DMA 完成及最近有效帧的 64 位时刻，main.c 在完成/有效路径更新时间，并最多每 10 ms 读取诊断。500 ms 阈值检测持续停滞，不代替原来的逐帧错误/间隙计数。最初一直没帧时明确保留“等待第一张完整图像”。

状态元数据由 66 字增加到 72 字。TCP op=3 使用版本化健康字段覆盖原有前六个性能诊断字，op=4 仍可读原始性能诊断。所有图像描述不变，响应头仍为 276 B，并继续验证头部 CRC。旧固件没有健康字段时保持兼容，不伪造状态。

工作站优先处理待确认与重启对账，健康握手不打乱原来的确认顺序。正常取图完成后的状态可复用；只有超过 200 ms 或等待中才追加状态读取，避免每帧无条件多一次网络往返。

## 分层验证

138 项主机测试通过，包括新协议字段、异常状态拒绝、旧版本兼容、启动等待、手动请求保留/取消、故障时排空已有证据以及状态过期显示。旧测试桥显式代表不提供健康握手的早期固件，新测试桥独立开启握手路径。

实际 C 编译测试通过 {len(n['boundaries'])} 个边界场景和 {n['random_operations']:,} 次随机操作，覆盖 499/500 ms 边界、64 位时刻超过 32 位毫秒范围、年龄饱和、DMA 所有错误位、停止与错误优先级。实际 main.c/MMIO 模型另验证 10,000 次快速循环不读额外寄存器、100 Hz 更新、有效与损坏描述的时间戳差异。原生 CRC 的 3000 组独立 zlib 对照、1280 个描述单比特错误拒绝、48 槽所有权回归均通过。

## 实际开发板故障验证

使用本版正式 ELF 和原有 FPGA 配置，在真实 HDMI 输入下保留一张待确认图。测试通过守卫过的 JTAG 操作分别关闭 PL 新帧使能、清除 S2MM Run/Stop 位。每次都先核对本版版本、启动号和唯一待确认事件，不写图像、描述或槽引用。

| 注入操作 | 正式固件检测状态 | 原 active 标志 | 等待期间响应字节/s |
|---|---|---:|---:|
{health_rows}

两种故障下原待确认图像都再次以 RAW 和 RLE 读取，全部像素和描述逐字节相同，像素、头部和 PL 描述三类校验通过。正式工作站排空这一条证据后继续显示网络在线与采集故障；3 秒观测窗口没有新整帧请求，只有状态响应，已有图像保持明确的过期提示。

输入门控恢复后重新收到有效完整帧，并验证同一启动号下的新图三类 CRC。DMA 停止试验结束重新下载干净固件，没有直接假设原环和部分帧可继续使用。故障过程可能丢失帧，相关计数保留在分阶段 JSON 中，不用清零掩盖；正常回归另从干净启动开始。

上述是可控输入门控与 DMA 停止，不是物理 HDMI 拔插或断电试验。启动等待、持续无效包等其余状态有原生/主机测试，本版没有逐项宣称全部实板故障注入覆盖。

## 正常回归与传输

50 对同事件 RAW/RLE 图像逐字节相同；9 类断连/损坏数据、3 类主机退出/实际 JTAG 重载、正式 UI 的待确认恢复均通过。UI 恢复只进行原事件的 stats/ACK/stats，没有新增取图。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体减少 % |
|---|---:|---:|---:|
{rows}

这是应用请求耗时的小样本实测，包含帧等待等因素；不能宣称压缩在所有内容上都更快，复杂噪声会自动回到 RAW。

连续运动 {c['seconds']:.3f} 秒，电脑收到 {c['host_captures']} 张抽样/事件图，保存 {c['saved']} 个不同缺陷产品。最大居中误差 {a['max_center_error_px']} px，独立参考掩码、区域框、面积和来源身份一致。正常窗口没有新增 gaps、invalid、dropped、ACK 或描述 CRC 错误，健康状态无误报。

冻结预览仍接收必要事件，应用层接收字节率减少 {b['received_rate_reduction_percent']:.3f}%，10 个预期缺陷事件全部留存。该统计不含链路开销，也不代表桌面预览 60 fps。结束恢复连续真实照片输入、仅预览和 1 GiB 存档上限，避免测试长期产生海量图片。

## 产品优势、限制与下一步

优势是像素算法在 FPGA 持续运行，ARM/电脑的网络等待不直接阻塞像素处理；证据与坐标同帧、有产品身份、完整性校验和确认恢复。现在还能区分网络问题与完整采集问题，故障可观察，不再只显示一个模糊“在线”。

仍是竞赛原型：真实照片合成运动不是现场相机；弱裂纹对强种子依赖、跨材料误报、有限 12 事件缓存、掉电丢失未存 DDR、HDMI 上一帧框、既有 CDC、长周期身份、单接收端和 PNG/SQLite 跨文件一致性仍未解决。V1.6 开发集的改善不能冒充独立工厂准确率。

下一版先做有界恢复的可行性和包边界验证；必要时新增硬件复位/清空接口。恢复要保留已排队证据、明确标记中断中的产品、等待新的 START，再恢复自动留图。不能通过反复复位、提高时钟或忽略校验来隐藏错误。详细见 下一版_有界恢复设计.md；本科答辩原理见 V1.19_采集健康监测原理.md。
'''
(R/'docs/Tile_V1.19_采集健康监测与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.19

完整图像采集健康监测：网络在线、启动等待、停帧、无效数据、DMA 错误/停止分别可见。无新图时只轮询状态，已排队证据仍可取回。

- 工程：pynq_z2_tile_v1_53.xpr；Vitis workspace：pynq_z2_tile_v1_53.sdk。
- 完整构建：.sdk/build_ethernet.py；下载：.sdk/program_ethernet.bat；启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.19_采集健康监测与实板报告.md；原理与后续设计同目录。
- FPGA 沿用 V1.15；本版不自动 DMA 复位。V1.18 原工程与 ZIP 备份均保留。
- control_capture_health.tcl 是维护测试工具，日常使用不要运行。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.19 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.19 / 采集健康监测</p><h1>网络在线，图像也需要独立检查</h1><section><strong>实板停帧与 DMA 停止均被发现</strong><p>已有证据 RAW/RLE 逐字节不变。排空后仅轮询状态，不反复请求不存在的新帧。</p></section><section><h2>正常采集没有健康误报</h2><p>138 项主机测试、18 个 C 边界与 25,000 次随机操作。50 对实际图像、9 类故障、3 类重启和 UI 恢复通过。</p><p>连续留图最大居中误差 {a['max_center_error_px']} 像素；冻结预览字节率下降 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>验证范围</h2><p>输入门控与 DMA 停止是受控故障；不是物理 HDMI 拔插。本版只监测与等待，尚不自动 DMA 复位。FPGA 算法和硬件保持，工厂数据仍需独立验证。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.19 report generated from passing fresh evidence')
