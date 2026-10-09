from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_21'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
fw=read(O/'firmware_audit.json');w=read(O/'admission_board/summary.json');old=read(O/'old_pause_counterexample.json')
n=read(O/'dma_recovery_native.json');h=read(O/'health_native.json');dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json');ui=read(O/'ui_restart_after.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json')
assert all(x['passed'] for x in (fw,w,n,h,dc,sc,t,f,r,ui,c,a,b)) and sg['result']=='PASS' and old['undesired_new_capture']
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 160 tests' in units and units.rstrip().endswith('OK')
assert len(w['cases'])==4 and all(x['passed'] for x in w['cases'])
baseline=read(B/'DELIVERY_MANIFEST.json');assert baseline['status']=='BOARD_VALIDATED_FRAME_BOUND_GENERATION_WITH_KNOWN_LIMITS'
summary=dict(version='V1.22',passed=True,firmware=fw,admission_board=w,old_counterexample=old,recovery_native=n,health_native=h,unit_tests=160,
 transport=t['summary'],faults=f,restarts=r,ui_restart=ui,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,
 inherited_recovery_evidence=dict(version='V1.21',manifest=str(B/'DELIVERY_MANIFEST.json'),sha256=hashlib.sha256((B/'DELIVERY_MANIFEST.json').read_bytes()).hexdigest(),scope='Previous actual DMA recovery/generation evidence; this release reruns actual C recovery and audits firmware changes limited to version labels, not a new physical DMA halt campaign'))
(O/'capture_admission_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
testrows='\n'.join(f"| {x['name']} | {'有' if x['queued_before'] else '无'} | {' → '.join(x['operations'])} | {x['after']['captures']} | {x['after']['capture_control']['cancelled_before_capture']} |" for x in w['cases'])
transport='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
doc=f'''# Tile V1.22 停止接收与取图同步报告

## 本版解决什么

状态检查还没返回时按“停止接收”，旧版可能在状态返回后继续发一次取图。V1.21 受控桥已复现：停止之后出现 stats → capture → ACK → stats。本版在真正允许整帧请求之前再次核对停止代次，旧请求意图被取消，已有排队图不被取走或确认。

已经允许开始处理的图像继续完成校验、按存储策略保存与确认。停止不会强行截断半张图，也不会使已保存证据丢失待确认身份。失败的在途请求在停止后不再自动重试。

界面现在区分状态检查、参数提交、图像读取、待确认核对、ACK 和确认后状态，并记录允许开始取图与检查点取消的次数。

## 保存与构建

旧工程 D:/Vivado/pynq_z2_tile_v1_21 完整保留；新工程 D:/Vivado/pynq_z2_tile_v1_53，Vivado 使用同名 .xpr，Vitis workspace 为同名 .sdk。备份 D:/Vivado/_baseline_backups/tile_v1_21_before_v1_22.zip，SHA256 517a91e5700d812af8c5ad33ccf7ebeafbb10b43aebc53bd8692f8f29cb48c45。

Vivado 建立正常工程结构，FPGA BIT/XSA/LTX 沿用 V1.15。Vitis 完整构建，ELF SHA256 {fw['elf_sha256']}。严格源码审计确认 ARM 固件只改变版本常量和文字标签，没有改变检测、DMA、队列、恢复和代次逻辑；实际中断浮点保护、4 KiB IRQ 栈及整数 memcpy 保留。本版没有新的布局布线、频率或识别精度结论。

## 原理和处理边界

接收轮次保存启动时的 epoch。停止在锁内关闭接收并递增 intent_epoch。预检查完成后，再在同一把锁内判断 `epoch == intent_epoch` 且仍有本轮有效意图；不满足则取消。通过时将阶段置为 CAPTURE、计数加一，释放锁后才进行耗时的网络读取。

这个检查点给“停止”和“允许开始”确定先后关系。停止若晚于检查点，本次已经允许开始的请求可以完成；不能表述成点击停止后绝不会再有任何网络字节。停止后马上重新开始也不会让旧轮次复活，下一轮负责新意图。

FPGA 继续按 720p60 处理像素、裂纹候选、区域框、产品与最佳帧判定。ARM 按 PL 标志管理 DDR 引用和事件、压缩、网口、恢复及代次。电脑增加的是接收线程控制，未引入软件图像识别。

## 实板受控调度验证

所有状态与像素来自真实开发板。测试在真实状态/图像已收到后，向接收线程交付之前加受控等待；ACK 场景在发确认之前等待。然后执行暂停，释放屏障，核对实际板端 request/head/tail/depth、像素和数据库。这是主机调度测试，不是虚构状态，也不是声称模拟了网线物理故障。

| 场景 | 初始有排队图 | 接收线程操作 | 取图数 | 检查点取消数 |
|---|---|---|---:|---:|
{testrows}

空队列和已有队列的状态等待均被取消，没有新取图，板端请求/队列身份不变。已有排队图再次读取逐字节相同、三类 CRC 通过，清理确认在测试核对后显式执行。已开始的手动图完成一次保存与 ACK；已保存待确认场景也完成原事件，没有启动下一张。

160 项独立主机测试通过，新增 8 项涵盖手动请求、排队事件、停止后立即开始、冻结预览参数提交、已开始图像/ACK 以及停止后的失败不重试。第一次测试发现 unittest 收集了导入的旧测试类，产生重复项；已改为模块导入，最终唯一测试数为 160，没有把重复执行算作额外覆盖。

实际 C 回归包含 20 个恢复/代次场景、健康监测边界和随机检查、3000 组描述 CRC 独立对照、1280 个单比特拒绝及 48 槽所有权。V1.21 的实际 DMA 三次恢复/第四次停止与代次证据作为继承证据保留；本版没有重跑整套物理 DMA 停止试验，不能把旧结果说成新一轮实测。

## 正常功能回归

50 对实际图 RAW/RLE 逐字节一致，9 类网络故障、3 类程序退出/实板 JTAG 重载和正式 UI 待确认恢复通过。UI 仅 stats/ACK/stats，零新取图，原 PNG 不变。

| 输入 | RAW 中位 ms | 自适应中位 ms | 图像体字节减少 % |
|---|---:|---:|---:|
{transport}

请求耗时包含等待，并非纯链路极限；难压缩噪声回到 RAW。连续运动 {c['seconds']:.3f} 秒，接收 {c['host_captures']} 张预览/事件图，10 件预期缺陷产品全保存，最大居中偏差 {a['max_center_error_px']} 像素。独立参考掩码、框、面积、来源身份一致，正常窗口无新增 gaps、invalid、dropped、ACK 或描述 CRC 错误。

冻结预览仍接收必要事件，应用层字节率减少 {b['received_rate_reduction_percent']:.3f}%，10 件事件全部留存。它不是电脑预览 60 fps 的结论。结束恢复真实照片连续运动、仅预览和 1 GiB 容量上限。

## 使用方法

USB 接板 PROG UART；电脑 HDMI → 板 HDMI IN；板 HDMI OUT → 显示器；板网口直连电脑。输入仍为 1280×720、60 Hz。使用本版 .sdk/program_ethernet.bat，再启动本版“启动以太网工作站.bat”。

停止时观察“当前传输”：检查状态中的停止会取消随后的新取图，已经开始的图像/确认会完成后变为空闲。有待确认证据时可单独恢复确认，不必重新抓图。冻结预览仍是后台接收，和停止不同。

回退先停止当前程序和播放器，再使用 V1.21 配套下载文件与工作站。不要把任意新固件与不理解协议的旧工作站混搭。

## 剩余限制与下一步

当前是 FPGA 工业视觉竞赛原型。真实照片合成运动不等于工厂相机实测；弱裂纹种子依赖、跨材料误报、独立盲测缺失、高速居中偏差、HDMI 前一帧框、已有 CDC、有限事件缓存、掉电丢失未存 DDR、完整长期身份周期和中断最坏栈仍是限制。CRC 不是网络认证；PNG 与 SQLite 也不是跨文件原子事务。

停止控制的明确边界是取图允许开始的检查点，不能把它宣传成任意时刻撤销已经在途的证据。下一步可以继续审查协议版本混用与状态显示可靠性，再回到真实材料弱裂纹的独立数据评估；算法调整要另起小版本，与已有稳定传输和存档基线比较。

收尾审查另发现一个独立问题：独占锁住 HDMI 命令文件时，一次实际 `/api/state` 请求异常断开；释放后立即恢复，采集继续。这不是本版停止竞争修复的失败，已保留 `reports/v132/state_file_lock_counterexample.json` 反例，将在下一小版专门修复状态读取和播放器确认显示。

本科答辩解释见 V1.22_停止与在途请求原理.md。机器证据见 reports/v132/capture_admission_validation_summary.json，最终封存状态以 DELIVERY_MANIFEST.json 为准。
'''
(R/'docs/Tile_V1.22_停止接收与取图同步报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.22

修复状态预检查期间停止后仍启动新取图的竞争。已开始图像和已保存证据继续完成当前确认；界面显示准确的处理阶段。

- Vivado：pynq_z2_tile_v1_53.xpr；Vitis workspace：pynq_z2_tile_v1_53.sdk。
- 构建：.sdk/build_ethernet.py；下载：.sdk/program_ethernet.bat；启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.22_停止接收与取图同步报告.md；学习：docs/V1.22_停止与在途请求原理.md。
- V1.21 原工程和 ZIP 均保留；FPGA 与 ARM 算法/通道行为保持，固件仅更新版本标签。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.22 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.22 / 接收控制</p><h1>停止取消尚未开始的取图，当前证据完整收尾</h1><section><strong>实板 4 个受控调度场景通过</strong><p>状态等待中停止：零取图，排队像素不变。图像/确认已经开始：当前图保存与确认完成，不取下一张。</p></section><section><h2>160 项独立主机测试通过</h2><p>50 对实际图、9 类网络故障、3 类重启、UI 确认恢复及连续产品回归通过。最大居中误差 {a['max_center_error_px']} 像素；冻结预览字节率减少 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>停止的边界</h2><p>检查点之后已经允许开始的请求可完成，不是强行截断 TCP。FPGA 持续检测；真实照片回放仍不能证明工厂识别精度。本版固件仅版本标签变化。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.22 report generated from passing fresh evidence')
