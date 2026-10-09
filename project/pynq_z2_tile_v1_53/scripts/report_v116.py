from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_15';O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
irq=read(O/'irq_context/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
n=read(O/'descriptor_native.json');slot=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
assert all(v['passed'] for v in (irq,fw,t,f,r,c,a,b,ui,n,slot)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 120 tests' in units and units.rstrip().endswith('OK')
old=read(B/'reports/v115/transport_comparison.json');comparisons={}
for name,v in t['summary'].items():
 prev=old['summary'][name]
 comparisons[name]=dict(raw_median_change_percent=(v['raw_request_ms']/prev['raw_request_ms']-1)*100,
                        compact_median_change_percent=(v['compact_request_ms']/prev['compact_request_ms']-1)*100)
summary=dict(version='V1.16',passed=True,firmware=fw,irq_context=irq,unit_tests=120,native_descriptor=n,
             transport=t['summary'],prior_release_latency_comparison=comparisons,faults=f,restarts=r,ui_restart=ui,
             station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,
             hardware_origin='Unchanged, hash-verified V1.15 BIT/XSA/LTX; no new place-and-route claim')
(O/'irq_context_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
base,new=irq['baseline'],irq['candidate']
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} | {comparisons[name]['compact_median_change_percent']:+.2f}% |" for name,v in t['summary'].items())
doc=f'''# Tile V1.16 中断现场保护与实板验收报告

## 本版解决的问题

V1.15 的真实 ELF 使用 hard-float ABI，但中断入口没有启用浮点上下文保存。编译器或库可以在没有显式浮点算法的情况下使用这些寄存器，因此只保留通用寄存器存在配置缺口。本版通过 AMD BSP 的正式配置接口启用异常入口已有的保存/恢复实现，并保留已验证的整数 memcpy。

这次先用实际旧 BSP 做失败对照，再测新 BSP。受控试验确认旧入口不能隔离处理函数合法的 FP 改写、新入口可以恢复；不把它描述为当前 Ethernet ISR 新近发生的一次现场损坏。视觉算法仍全部在 FPGA。

## 工程与备份

工程位于 D:/Vivado/pynq_z2_tile_v1_53，Vivado 工程为 pynq_z2_tile_v1_53.xpr，Vitis workspace 为同名 .sdk 目录。已建立可打开和继续构建的 BD/工程结构，但本版直接沿用 V1.15 已实现的 BIT/XSA/LTX，逐一比较哈希一致。没有伪称重新布局布线。

V1.15 原工程完整保留，源码、文档和下载文件另备份至 D:/Vivado/_baseline_backups/tile_v1_15_before_v1_16.zip。备份哈希和前版源码逐文件核对见 ITERATION_PLAN.json 与 DELIVERY_MANIFEST.json。

## 实现改动

- build_ethernet.py 使用 domain.get_config/set_config 读取并保留原 BSP 额外编译参数，追加 FPU_HARD_FLOAT_ABI_ENABLED=1。
- 源链接脚本中的 IRQ 栈从 1024 增至 4096 字节，增加 3072 字节 DDR 预留。完整构建和仅应用重建都从同一源码导入。
- 最终 ELF 中核对 d0～d7、d16～d31、FPSCR、FPEXC 的实际成对保存/恢复；额外 200 字节，加原通用寄存器入口共 224 字节。
- 整数 memcpy、网络格式、CRC、产品最佳帧、视觉阈值和硬件时钟保持。固件版本为 0x00011000，工作站标识为 V1.16。

初次发布核对发现源码与生成链接脚本不一致：当时只在生成副本扩充栈。已把修改落实到源文件，重导入并重新链接，再核对两份字节相同。此次没有把未通过一致性检查的构建下载。

编译器保留了工具生成 CMake 的 Windows 路径转义警告；诊断链接还报告 AMD 启动对象缺少 .note.GNU-stack。构建和最终检查通过，日志原样保留，不宣称零警告。

## 真实中断新旧对照

两个诊断 ELF 使用同一源码，分别链接实际 V1.15 与 V1.16 BSP，诊断栈均为 1024 字节，避免用不同测试条件掩盖变化。主程序填入 32 个 d 寄存器哨兵，触发实际 GIC SGI，处理函数改写 ABI 允许改变的 24 个寄存器及 FPSCR，再通过实际 IRQ 返回。任何打印和其他 C 调用发生前即保存返回值。测试核对主程序在独立的系统/管理栈，处理函数实际在 IRQ 模式执行。

| 指标 | 旧入口（预期状态丢失） | 新入口 |
|---|---:|---:|
| 实际中断数 | {base['actual_interrupts']} | {new['actual_interrupts']} |
| 不一致的测试轮数 | {base['bad_iterations']} | {new['bad_iterations']} |
| d 寄存器不一致次数 | {base['register_mismatches']} | {new['register_mismatches']} |
| FPSCR 不一致次数 | {base['fpscr_mismatches']} | {new['fpscr_mismatches']} |
| FPEXC 不一致次数 | {base['fpexc_mismatches']} | {new['fpexc_mismatches']} |
| 超时 | {base['timeouts']} | {new['timeouts']} |
| 栈高水位，字节 | {base['stack_high_water_bytes']} | {new['stack_high_water_bytes']} |
| 往返平均耗时，微秒 | {base['roundtrip_mean_us']:.3f} | {new['roundtrip_mean_us']:.3f} |
| 往返最大耗时，微秒 | {base['roundtrip_max_us']:.3f} | {new['roundtrip_max_us']:.3f} |

底部 64 字节保护区完整。时间包含 SGI 触发、入口、分发、处理函数、返回和观察；诊断关闭数据缓存，不能把该时间直接当成正常网口中断延迟。栈高水位只覆盖本条调用链，不是所有中断分支的最坏情况。FPEXC 仅核对前后与实际保存指令，没有故意关闭执行单元。没有测试嵌套 IRQ、实际 FIQ 或异常/中止嵌套。

诊断结束重新下载完整 V1.16 BIT 与正式 ELF，恢复网口工作站。诊断期间的停机不计入正常运行零间隙验收。

## 正式固件回归

120 项软件回归通过。实际 C 的 3000 个描述 CRC 与独立 zlib 一致，1280 个单比特描述错误被拒绝；帧槽共享、最佳帧替换、ACK 顺序、48 槽、队列满和无效帧路径通过。硬件源码/约束和下载文件哈希与 V1.15 相同，因此不重复宣称一次新的 RTL/实现验收；新硬件的原始证明在 V1.15 报告。

重新进行了 50 对同一实板事件的 RAW/自适应传输，像素逐字节一致，整帧、头部身份和 PL 描述校验通过。9 类网络/数据故障、3 类实际程序退出/JTAG 重载和正式 UI 待确认恢复通过。UI 恢复零次新增采集，保留原图与复核数据。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体减少 % | 自适应耗时相对 V1.15 |
|---|---:|---:|---:|---:|
{rows}

比较是相邻版本分时运行的应用层请求/解码/校验时间，包含电脑与调度波动，不是严格交错随机的性能实验，也不等于 HDMI 帧率。不可压缩内容使用 RAW 回退；可靠性修复不应通过关闭中断来制造网速收益。

连续真实照片运动 {c['seconds']:.3f} 秒，主机接收 {c['host_captures']} 次，10 块缺陷瓷砖各留一张完整证据，最大居中误差 {a['max_center_error_px']} 像素；像素掩码、框和面积与独立参考一致。窗口内未新增间隙、无效帧、队列丢失、ACK 错误或描述 CRC 错误。

后台冻结预览测试接收字节率下降 {b['received_rate_reduction_percent']:.3f}%，10 个预期事件均保存。验收后恢复真实照片连续移动、仅预览、不再自动存图，默认 1 GiB 存档上限。主档保留 24 张自动证据和 1 张恢复测试证据。

## 产品职责与进度

FPGA：720p60 裂纹候选、双阈值邻域支持、区域红框、产品跟踪、最佳帧质量信息、像素/描述 CRC。ARM/Vitis：DMA/DDR 帧槽所有权、事件队列、整数数据复制、自适应无损压缩、以太网及中断现场保护。电脑：预览、同帧叠框、接收完整性校验、容量控制、证据复核和待确认恢复。

本版是可靠性改进，不是新的弱裂纹准确率结果。当前输入是真实瓷砖照片经 HDMI 合成运动，不是真实工厂相机盲测。

## 操作与回退

保持电脑 HDMI 720p60→开发板 HDMI IN→HDMI OUT→显示器，PROG UART USB 与电脑直连网线。下载 .sdk/program_ethernet.bat，再运行根目录“启动以太网工作站.bat”。诊断脚本只用于专门维护测试，不应当成日常应用启动。回退先停止当前服务，再下载并启动完整 V1.15。

## 下一步与仍有的限制

优先处理完整 32 位事件编号回绕：当前 ACK=0 被跳过，容量为 12 的队列用递增计数取模也会在 2^32 回绕处破坏物理槽顺序。需要独立物理读写索引、回绕感知协议检查和跨边界故障测试，不能只删掉 ACK=0 判断。

之后处理 HDMI 消失/恢复时的 DMA 有界恢复、旧 JTAG 图像取图地址界限、既有 5 个 CDC 不安全端点和高速居中偏差。继续独立材料数据集的弱裂纹召回/纹理误报评估。

12 事件有限缓存、板卡掉电后的未保存 DDR 数据、PNG/SQLite 非跨文件事务、单接收端、HDMI 使用上一帧坐标等边界仍在。CRC 不是安全认证。4 KiB 栈与本次 SGI 试验不能替代完整最坏路径、异常嵌套和长期压力验证。

原理、公式、ABI 和测试方法见 docs/V1.16_中断现场保护原理.md。
'''
(R/'docs/Tile_V1.16_中断保护与实板报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.16

通过 BSP 配置启用 Cortex-A9 IRQ 浮点现场保护，正式 IRQ 栈 4 KiB，保留整数 memcpy。FPGA 采用与 V1.15 哈希相同的 BIT/XSA/LTX。

- Vivado：pynq_z2_tile_v1_53.xpr；本版没有改动 PL。
- Vitis workspace：pynq_z2_tile_v1_53.sdk；完整构建 build_ethernet.py。
- 下载：.sdk/program_ethernet.bat；工作站：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.16_中断保护与实板报告.md。
- 原理：docs/V1.16_中断现场保护原理.md。
- 10000 次真实 IRQ 新旧对照、120 项软件回归及实际传输/故障/连续留图通过。
- 默认仅预览、存档上限 1 GiB。V1.15 原工程和轻量 ZIP 已保留。

验证范围与未完成事项见报告；不以中断可靠性改进冒充算法准确率提升。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.16 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.16 / ARM 中断现场保护</p><h1>中断返回后，数据处理状态保持完整</h1><section><strong>10,000 次实际 IRQ，零状态丢失</strong><p>旧 BSP 受控对照出现预期的寄存器丢失；新 BSP 全部恢复。相同诊断栈下高水位 {base['stack_high_water_bytes']} → {new['stack_high_water_bytes']} 字节；正式工程预留 4 KiB。</p></section><section><h2>再验证正常图像链路</h2><p>120 项软件回归、50 对实板 RAW/压缩图像、9 类网络故障、3 类重启与 UI 待确认恢复通过。</p><p>连续测试每块缺陷瓷砖留一张完整图，最大居中误差 {a['max_center_error_px']} 像素；后台节流 {b['received_rate_reduction_percent']:.2f}%。FPGA 与 V1.15 完全相同。</p></section><section class="warning"><h2>边界仍需明确</h2><p>受控 SGI 不是所有网口中断路径、嵌套中断或长期稳定性的穷尽证明；本版没有新的识别准确率结论。计数回绕、HDMI 恢复、CDC 和独立材料盲测仍待改进。</p><p>默认仅预览，存档上限 1 GiB。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.16 report generated only from passing fresh actual-board evidence')
