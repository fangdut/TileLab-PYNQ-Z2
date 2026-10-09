from pathlib import Path
import json

R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
n=read(O/'dma_recovery_native.json');h=read(O/'health_native.json');w=read(O/'dma_recovery_board/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
assert all(v['passed'] for v in (n,h,w,fw,t,f,r,c,a,b,ui,dc,sc)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 144 tests' in units and units.rstrip().endswith('OK')
summary=dict(version='V1.20',passed=True,firmware=fw,recovery_native=n,health_native=h,recovery_board=w,unit_tests=144,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,
             station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,hardware_origin='Unchanged V1.15 BIT/XSA/LTX; IRQ context, ring wrap, ACK isolation and capture health retained')
(O/'dma_recovery_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
fault_rows='\n'.join(f"| {v['number']} | {v['after']['capture_recovery']['state']} | {v['after']['capture_recovery']['last_duration_ms']} | {v['final_stats']['invalid']-v['before']['invalid']} | {v['final_stats']['gaps']-v['before']['gaps']} |" for v in w['cases'])
term=w['cases'][3]['terminal_wait']
doc=f'''# Tile V1.20 有界 DMA 自动恢复与实板验收报告

## 交付结果

本版在正常采集后发生明确 DMA 停止或错误时自动恢复 DMA 接收，保留已排队截图，验证完整包后才允许新证据进入队列。每次启动最多自动尝试 3 次，失败、超时或超过次数上限后停止采集并显示原因，网络与旧证据读取继续工作。

真实开发板上连续注入 4 次 S2MM 停止：前三次恢复，第四次按上限停止。每次都保留未确认截图并重新读取 RAW/RLE，像素与描述逐字节相同。恢复后的当前产品不再自动完成旧证据，必须等新的产品 START；下一件产品正常保存。

## 版本与备份

- 工程 D:/Vivado/pynq_z2_tile_v1_53，正常 Vivado .xpr 结构，Vitis workspace 为同名 .sdk。
- V1.19 完整旧工程保持，轻量源码/下载文件备份为 D:/Vivado/_baseline_backups/tile_v1_19_before_v1_20.zip。
- ZIP SHA256 cafeef60c66b0cda24f3b4195f3f27ec643378e94810535de4d6787676ea71bb。
- FPGA BIT/XSA/LTX 与已验收 V1.15 完全相同，本版没有重新布局布线，也没有提高像素时钟。Vivado 重新建立工程，Vitis 完整构建平台和应用。
- ELF SHA256 {fw['elf_sha256']}；text 131598 B，data 3476 B，bss 7435728 B，text 比 V1.19 增加 1728 B。
- 反汇编核对中断浮点现场保护、4096 B IRQ 栈、整数 memcpy；作者源码与导入源码一致，队列确认逻辑不变。

## 硬件、Vitis 与电脑各做什么

FPGA 持续处理 720p60 像素流：灰度、方向暗谷与弱裂纹支持、候选掩码、区域框、产品身份与最佳帧更新标志、像素和原始描述 CRC。FPGA 的产品/最佳帧判定仍是依据。

ARM 根据 FPGA 标志保留或替换 DDR 中的最佳帧槽，在产品结束时发布事件；它不在软件中重新识别裂纹。除此之外，ARM 维护 32 个 DMA 描述符、48 个帧槽、12 项事件队列、无损传输、确认、采集健康状态及本版的有界恢复。电脑验证身份和三类 CRC，显示同帧框、存档、人工复核。

因此这是带证据留存的 FPGA 工业视觉竞赛原型，并非仅显示红框的视频播放器；但现有照片合成运动也不是实际工厂相机精度证明。

## 恢复的工作顺序

1. 每 10 ms 最多检查一次 DMA。仅 DMA 错误位或收到过有效帧后的停止状态触发恢复；启动未收到图、单纯停帧、故意关闭采集门控不自动复位。
2. 关闭新帧入口，释放独立的“当前最佳帧”引用，保留所有排队事件引用，置等待新产品标志。
3. 只写一次 DMA reset，后续循环检查完成，最多等待 1 秒。网络和确认服务不中断，不使用长时间忙等。
4. 重建 32 个描述符，选槽时排除排队证据和其他持有引用的槽。重新开放采集。
5. 接收包必须满足长度、SOF/EOF、魔数和描述 CRC。丢弃残留短包，连续两张完整有效帧在 3 秒内到达才恢复正常发布。
6. 恢复期间仍记录无效包和帧间隙。验证帧计数但不发布成新证据。恢复后手动/预览可以取新完整帧，自动产品事件等待新的 START，旧产品 EXIT 不能发布被中断的旧最佳帧。
7. 超时、再次报错、无可用槽或第四次故障进入 FAILED。已有证据仍可读取确认；失败不会反复重启，日常维护通过重新下载干净正式固件恢复。

连续两帧到达时刻必须严格早于验证截止时刻。测试包含“第二帧及时到达但下一次轮询稍晚”和“第二帧恰好在截止时刻到达”，避免把轮询调度延迟与有效帧超时混淆。

## 协议和界面

状态元数据从 72 字增加至 86 字。TCP 状态使用版本化的 14 字恢复诊断，响应头仍为 276 B，图像描述布局不变。包括状态、尝试/成功/失败数、原因、最后 DMA 状态、中断产品观察次数、丢弃包、等待新产品、次数和时间上限以及最后恢复耗时。

中断产品观察次数只是故障时观察到产品的次数，并非对故障期间所有实际漏检产品的精确计数。恢复计数目前是实时状态，尚未写入每条截图的持久身份，这是下一版改进点。

电脑显示恢复中、恢复失败和次数。空队列且无完整帧时只轮询小状态包；已有队列先排空。待确认日志及重启对账仍优先，不因恢复状态丢弃旧图。

## 分层测试

144 项主机测试通过。实际 main.c 的 C 测试覆盖 16 个恢复场景：所有 DMA 错误位、12 项队列与共享槽、32 个新描述符不覆盖旧证据、短包重置连续验证计数、两类超时边界、验证期间再报错、3 次上限、空闲等待不误复位、无可用槽及失败后旧 ACK 仍可处理。

这些原生测试使用模拟 MMIO/时间和映射的描述符内存，不宣称模拟物理 AXI 总线。继承健康监测 18 个边界与 25,000 次随机操作，实际 main 的 100 Hz 采样约束也通过。3000 组独立 zlib 描述 CRC 对照、1280 个单比特损坏拒绝、48 槽所有权回归通过。

## 实际开发板故障注入

使用正式 V1.20 ELF、真实 HDMI 输入。守卫脚本先核对版本、启动号、唯一待确认事件和恢复次数，只清除 S2MM Run/Stop 位，不写像素、描述或队列引用。

| 第几次故障 | 状态 | 恢复状态机耗时 ms | 新增无效包 | 新增帧间隙 |
|---:|---|---:|---:|---:|
{fault_rows}

每次故障前未确认的图像和描述均保留，RAW/RLE 重读和三类 CRC 全部一致。前三次确认了旧产品不继续自动留图、新 START 后的新产品完整证据正常。第四次失败后正式工作站仍取回旧证据，随后 {term['seconds']:.3f} 秒仅收到 {term['status_bytes']} 字节状态响应，没有发起新整帧请求，网络在线。

上述耗时是固件从开始恢复到验证成功的计时，不是从故障发生到网页显示的端到端时延。首次故障检测还受 10 ms 轮询周期影响。故障注入结束重新下载干净固件，正常回归从新启动开始；故障期间真实计数完整保留，未清零掩盖。

实板覆盖的是 DMA Run/Stop 故障；不是物理 HDMI 拔插、供电中断，也没有在实板上让 reset 永久卡住。后者只在原生模型验证。

## 正常回归结果

50 对同一实际事件 RAW/RLE 逐字节一致。9 类网络断连/数据损坏、3 类主机重启/实际板卡重载和正式 UI 恢复通过。UI 恢复原事件只执行 stats/ACK/stats，零新取图，原 PNG 不变。

| 输入 | RAW 请求中位 ms | 自适应请求中位 ms | 图像体字节减少 % |
|---|---:|---:|---:|
{rows}

请求耗时包括等待等因素，不是纯链路吞吐量；复杂噪声回到 RAW，不能声称压缩在所有内容上均更快。

连续运动 {c['seconds']:.3f} 秒，电脑收到 {c['host_captures']} 张预览/事件图，10 个不同缺陷产品全部保存。最大居中误差 {a['max_center_error_px']} 像素，独立参考掩码、区域面积、框和照片来源身份一致；正常窗口无新增丢帧计数、无效包、队列丢弃、确认或描述 CRC 错误。

冻结预览仍接收必要事件，应用层接收字节率减少 {b['received_rate_reduction_percent']:.3f}%，10 个预期缺陷事件全保留。此统计不含以太网链路开销，电脑预览也不是 60 fps。完成后恢复真实照片连续移动、仅预览和 1 GiB 留存上限。

## 操作与回退

1. 供电正常，PROG UART USB 接电脑；电脑 HDMI → 板 HDMI IN，板 HDMI OUT → 显示器。电脑 HDMI 设置 1280×720、60 Hz，扩展桌面给播放器。
2. 板网口直连电脑，使用原有直连地址配置；从本版 .sdk/program_ethernet.bat 下载 BIT 与 ELF，再运行根目录“启动以太网工作站.bat”。
3. 检查界面版本、采集健康、固件版本及新图变化。若恢复失败，上限不会自行清零；先排空可读证据，检查接线和供电，再重新下载。
4. stop_dma_v120.tcl 是维护故障注入工具，日常展示不要运行。回退先停止当前服务与播放器，再使用 V1.19 自己的下载文件和工作站，避免混用版本。

## 优势、限制与下一步

本版把“发现采集坏了”推进到“有限地恢复，并保护已取得的证据”。像素算法不增加 ARM 计算负担，不需要盲目加时钟。每次恢复有明确上限与可见结果。

限制：故障期间的未保存帧不可恢复；有限 12 项队列和未持久化 DDR 不保证长时间离线或断电留存。弱裂纹依赖强种子、跨材质误报、缺少独立盲测、HDMI 前一帧红框、已有 CDC 与时序余量、高速居中偏差、完整身份周期、中断嵌套/最坏栈和 PNG/SQLite 跨文件一致性仍需改进。CRC 只检测意外损坏，不是安全认证。

下一版优先把恢复代次绑定到每条证据，使恢复前排队图、恢复后新图和数据库导出可区分，再做重启与重传回归。随后再考虑 HDMI 时钟/物理链路恢复和真实工厂数据。算法精度必须由独立数据评估，不能以传输与恢复通过替代。

本科答辩原理、状态机和超时公式见 V1.20_DMA恢复原理.md；具体机器可核验的证据见 reports/v132/dma_recovery_validation_summary.json 和 DELIVERY_MANIFEST.json。
'''
(R/'docs/Tile_V1.20_有界DMA自动恢复与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.20

有界 DMA 自动恢复：同次启动最多 3 次，完整帧验证后恢复发布，排队证据保留，自动留图等待新产品 START。

- Vivado：pynq_z2_tile_v1_53.xpr；Vitis workspace：pynq_z2_tile_v1_53.sdk。
- 构建：.sdk/build_ethernet.py；下载：.sdk/program_ethernet.bat；启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.20_有界DMA自动恢复与实板报告.md；原理：docs/V1.20_DMA恢复原理.md。
- V1.19 完整工程与 ZIP 均保留。PL 沿用已验证 V1.15，不提高时钟。
- stop_dma_v120.tcl 为维护故障测试，日常展示不要运行。
- 验收范围为可控 DMA 停止；并非物理 HDMI 拔插、断电或工厂识别准确率验收。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.20 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.20 / 有界 DMA 自动恢复</p><h1>恢复采集，同时保护已经取得的证据</h1><section><strong>3 次自动恢复，第四次明确停止</strong><p>实板恢复耗时 50 / 60 / 60 ms。旧图 RAW/RLE 逐字节相同；新产品正常留图。故障期间的帧间隙和无效包如实记录。</p></section><section><h2>正常功能回归通过</h2><p>144 项主机测试、16 个实际 C 恢复场景、50 对实际图像、9 类网络故障、3 类重启、UI 待确认恢复与连续运动留图。</p><p>最大居中误差 {a['max_center_error_px']} 像素；冻结预览接收字节率减少 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>验证范围</h2><p>可控 DMA 停止，不是物理 HDMI 拔插或断电试验。时间为固件恢复阶段，不是网页端到端时延。FPGA 算法与时钟不变；识别精度仍需独立工厂数据验证。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.20 report generated from passing fresh evidence')
