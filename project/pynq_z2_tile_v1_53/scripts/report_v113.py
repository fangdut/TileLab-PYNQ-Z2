from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');u=read(O/'ui_restart_after.json')
assert all(x['passed'] for x in (t,f,r,c,a,b,u))
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 114 tests' in unit and unit.rstrip().endswith('OK')
summary=dict(version='V1.13',passed=True,unit_tests=114,hardware_inherited_from='V1.11',transport=t['summary'],faults=f,restarts=r,ui_restart=u,station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b)
(O/'journal_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
restarts='\n'.join(f"| {x['name']} | {x['seconds']:.3f} | {', '.join(x['operations'])} | {x['history'][0]['status']} |" for x in r['cases'])
transport='\n'.join(f"| {name} | {v['raw_request_ms']:.2f} | {v['compact_request_ms']:.2f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
doc=f'''# Tile V1.13 待确认持久化与重启恢复报告

## 本版完成的产品行为

电脑已经保存了一张缺陷截图，但尚未收到板端确认回复时，关闭或异常退出程序不再丢失“还需要确认哪一张”的记录。重新打开工作站后，系统保持暂停并显示“恢复待确认”。恢复会先检查原图文件和身份，再读取板端状态；不会直接抓下一张瓷砖。

如果开发板已确认原事件，电脑只结束本地待确认。如果开发板重新启动，则保留旧截图、人工备注和重启异常记录，结束已经失效的旧确认，并明确提示重启期间未保存事件不可恢复；绝不拿新启动的相同事件编号去完成旧确认。

V1.12 原工程完整保留，并生成 _baseline_backups/tile_v1_12_before_v1_13.zip。ZIP 覆盖源码、文档及下载文件，运行数据仍在旧工程。备份 SHA256 和逐文件核对见 ITERATION_PLAN.json、DELIVERY_MANIFEST.json。

## FPGA、Vitis 和电脑分别做了什么

FPGA 仍是 720p60 实时视觉引擎：四方向暗谷、强弱阈值、邻域支持、区域框、产品身份和最佳帧决策、整帧像素 CRC。硬件沿用 V1.11 的已验收 BIT/XSA/LTX，本版不改变检测算法或时钟，也不声称重新完成布局布线。

Vitis 裸机固件继续管理 32 个 DMA 描述符、48 个 DDR 帧槽、12 个事件缓存、无损压缩、TCP 和响应头 CRC。ARM 不承担裂纹识别。本版重新构建并下载匹配 V1.13 版本号的固件，队列确认语义沿用原实现；主要新增恢复逻辑位于电脑端。

电脑端增加 SQLite 待确认槽和最多 64 条完成历史。证据行与待确认身份在同一数据库事务提交，先保存再 ACK；恢复核对 PNG 的 SHA256、目标连接、板卡启动号和队列位置。正常仅预览不写待确认日志，因此不会给每张预览增加磁盘写入。界面新增单独的恢复入口；“开始采集”也会先完成旧待确认，再继续新图像。

## 恢复判断和术语

ACK 是确认消息，head 是板端已经释放到的事件编号。同一启动号下，head+1 等于待确认编号且队列非空，说明旧事件仍在；head 等于该编号，说明已经确认；其他位置不作推测，暂停并保留记录。事件号按 32 位模运算，避免加一溢出产生错误比较。

ACK 回复本身必须具有正确状态魔数、相同启动号和匹配 head。CRC 正确只能说明传输未意外改变，不能代替这些语义检查。详细状态表、数据库事务和边界见 docs/V1.13_确认恢复原理.md。

## 软件回归

114 项回归全部通过，新增了程序重建后恢复、确认已执行、启动号变化、同一启动错误队列位置、目标连接不符、原图损坏、缺失数据库行、写日志失败、确认后的本地提交失败、保留人工结论、有限历史和错误 ACK 语义。

首次测试暴露完成历史的“创建时间”字段重名，造成状态接口异常，已把保存时间与完成时间分开。另有两个测试夹具需要适配新增参数和独立事件号，均修正并重跑。初始失败日志和最终通过日志都保留。Vitis 构建成功；工具生成 BSP 中的 CMake 路径警告保留在原日志，不冒充完全无告警。

## 实板传输与故障

50 对同一真实硬件事件的 RAW/自适应压缩图像逐字节一致，像素 CRC、响应头 CRC 都通过；部分断开后仍重读同一事件。9 类网络/数据故障通过：短断网、半包、ACK 回复丢失、RAW/RLE 颜色改变、CRC 字段改变、帧号改变、产品号改变和持续 30 秒不可恢复。损坏数据不保存、不确认；短暂连接问题有界恢复。

| 输入 | RAW 请求中位数 ms | 自适应中位数 ms | 图像体减少 % |
|---|---:|---:|---:|
{transport}

图像耗时是 TCP 应用请求及电脑解压/校验时间，不是 HDMI 帧率。难压缩噪声继续直接 RAW 回退。ACK 回复丢失场景现在先查状态，确认板端已经处理后完成本地记录，不再重复发送 ACK。

## 实际异常退出与板卡重下载

以下不是只模拟状态：独立测试进程实际在保存后用 os._exit 退出，没有执行清理函数；板端数据来自真实 HDMI/FPGA。第三项实际执行了本版 JTAG BIT+ELF 重新下载，产生新的启动号。它仍不等同于物理拔电测试。

| 实际场景 | 秒 | 恢复时操作 | 持久记录结果 |
|---|---:|---|---|
{restarts}

三个场景恢复后都没有额外抓图，只有原来 1 张证据；PNG 哈希和人工备注保持不变。板卡重新下载后不向新启动发送旧 ACK。重启前后计数属于不同运行，不能相减来宣称重启零丢帧。

还在正式工作站目录创建了 1 张真实“已保存、未确认”的手动截图，终止旧工作站进程并重新启动，通过浏览器实际点击“恢复待确认”。实测恰好执行状态、ACK、状态共 3 条请求，新增抓图为 0，旧图字节完全不变。截图与 before/after JSON 在 reports/v132。

## 连续运行和磁盘

正式接收线程连续运行 {c['seconds']:.3f} 秒，完成 {c['host_captures']} 次电脑接收，保存 {c['saved']} 张缺陷证据；掩码逐像素、区域框、面积、物理来源、唯一产品号与完整入镜检查通过，最大中心偏差 {a['max_center_error_px']} 像素。测试窗口没有新增采集间隙、无效帧、队列丢失或确认错误。

冻结后台实测接收字节率比正常预览降低 {b['received_rate_reduction_percent']:.3f}%，预期的 10 个缺陷事件均留存。统计为 TCP 应用层接收字节，含状态与 ACK，排除链路头。验收后恢复仅预览、真实照片连续移动、1 GiB 存档上限。本版主目录保留 24 张自动证据和 1 张手动重启测试图，另有有限故障测试证据，不会持续自动堆积截图。

## 使用

Vivado 工程：pynq_z2_tile_v1_53.xpr。Vitis 工作区：pynq_z2_tile_v1_53.sdk。下载 .sdk/program_ethernet.bat，启动根目录“启动以太网工作站.bat”。720p60 HDMI 输入/输出、PROG UART USB 和直连电脑网线保持原接法。

出现待确认提示时，“恢复待确认”只处理旧操作；“开始采集”会处理后继续。如果待确认文件被改变或目标连接不同，系统保持暂停并显示原因，不能删除原记录来假装处理成功。

## 限制与下一步

PNG 与 SQLite 不是一个跨文件事务，失败写入可能留下未登记 PNG；不会因此 ACK，它们仍计入容量。SQLite 同步提交不等于保证任何硬盘故障都能恢复。程序按一个电脑接收端使用一块板设计，多客户端并发未提供一致性保证。

未传到电脑的 DDR 图像在板卡重启后仍会丢失，本版只能保留已存证据并明确结束旧确认。物理拔线/拔电、数小时长时运行仍需后续测试。固件把 ACK=0 当作空请求，完整 32 位事件编号回绕仍有已知边界，需单独修复，不能承诺无限期不停机。PL 到 ARM 的描述字段还没有独立校验；下版优先保护这段元数据，使图像和硬件决策在进入 ARM 队列前也能检查。

检测算法本版没有改动。弱裂纹召回、跨材质误报、高速居中偏差、HDMI 前一帧红框、既有 CDC 端点、+0.011 ns 的 hold 余量和中断浮点上下文审计仍是已知空间。回放真实照片并不等于真实工厂相机采集，也不能得出泛化准确率。
'''
report='docs/Tile_V1.13_待确认恢复与实板报告.md';(R/report).write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.13

已保存截图的待确认身份持久化；程序重启先核对板卡启动号与队列，恢复旧确认，不额外抓图。

- Vivado：pynq_z2_tile_v1_53.xpr，沿用 V1.11 硬件。
- Vitis 工作区：pynq_z2_tile_v1_53.sdk；下载 program_ethernet.bat。
- 启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.13_待确认恢复与实板报告.md。
- 原理：docs/V1.13_确认恢复原理.md。
- 114 项软件回归；50 对实板图像；9 类网络故障；3 项实际进程退出/JTAG 重载；真实 UI 恢复；连续/冻结接收均通过。
- 旧 V1.12 完整保留并有 ZIP；默认仅预览，1 GiB 上限。

不能恢复板卡掉电前尚未传出的 DDR 图像。CRC、恢复机制不等于算法准确率。
''',encoding='utf-8')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.13 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.13 / 待确认持久化 · FPGA 继承 V1.11</p><h1>程序重启，继续处理原来那张证据</h1><section><strong>3 项实际重启测试 · 0 次额外抓图</strong><p>保存后进程异常退出、ACK 后异常退出、实际 JTAG 重新下载：原图和人工备注保留，启动号变化时不确认新事件。</p><p>正式界面“恢复待确认”也已实测：3 条请求、0 张新图。</p></section><section><h2>连续验证</h2><p>114 项软件回归；50 对图像逐字节一致；9 类网络与数据故障通过。</p><p>连续运动保存 10 张完整证据，最大中心偏差 {a['max_center_error_px']} 像素；冻结后台接收节流 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>仍有边界</h2><p>JTAG 重载不是物理拔电。未传出的 DDR 图像无法跨重启恢复。PL 到 ARM 的描述字段、长时运行和检测泛化仍需下一步验证。</p><p>默认仅预览，1 GiB 上限，完成历史最多 64 条。</p><a href="/api/benchmark">完整实测数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.13 report generated only from completed passing evidence')
