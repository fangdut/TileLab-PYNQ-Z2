from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_8'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
r=read(R/'reports/v132/recovery/summary.json');c=read(R/'reports/v132/station_continuous.json')
identity=read(R/'reports/v132/station_identity_audit.json')
assert r['passed'] and c['passed'] and identity['passed']
assert 'Ran 75 tests' in (R/'reports/v132/host_tests_final.log').read_text(encoding='utf-8-sig')
labels={'initial_3s_outage':'连接中断 3 秒','payload_cut':'仅发送部分图像后断开','ack_reply_lost':'板端执行确认后丢弃回复','corrupt_mask':'传输中掩码字节被改成非法值','bounded_30s_outage':'长时间无法连接'}
rows=[];web=[]
for case in r['cases']:
 vals=[labels[case['name']],f"{case['seconds']:.3f}",str(case['saved']), '自动恢复' if case['recovered'] else '拒绝数据、停止' if case['name']=='corrupt_mask' else '限时停止']
 rows.append('| '+' | '.join(vals)+' |');web.append('<tr>'+''.join('<td>'+v+'</td>' for v in vals)+'</tr>')
summary=dict(version='V1.9',hardware='V1.6 unchanged',unit_tests=75,recovery=r,source_identity=identity,continuous={k:v for k,v in c.items() if k not in ('records','rows','final_state')},transport_baseline=read(B/'reports/v18/transport_comparison.json')['summary'])
(R/'reports/v132/reliability_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
doc='''# Tile V1.9 可靠接收与画面同步报告

## 本版交付

V1.9 是在已验收 V1.8 上增加故障恢复的检测工作站。旧 V1.8 工程完整保留，源码和下载文件另存于 _baseline_backups/tile_v1_8_before_v1_9.zip；新工程和 .sdk 工作区独立。Vivado 创建正常工程及 BD，硬件配置沿用 V1.6；Vitis 平台和本版 ELF 重新构建并下载。FPGA 和 Vitis 的视觉职责没有变化。

FPGA 仍负责四方向暗谷、弱点邻域支持、区域红框、产品身份和最佳帧选择，720p60 实时采集。Vitis 的 ARM 程序负责 DMA/DDR 事件缓存、无损传输与应用确认；压缩预判沿用 V1.8。电脑本版负责传输恢复、完整性校验、存档、人工复核以及同步显示，不在生产流程重新识别裂纹。

## 改进一：短时网络故障自动恢复

原来一个请求内部的两次快速重试仍失败时，整个工作站会暂停。本版保留这层快速重试，在工作站外层增加 30 秒的恢复窗口，等待间隔依次为 0.25、0.5、1、2 秒，之后每 2 秒重试。界面显示正在恢复、尝试次数和剩余窗口。

只有网络操作抛出的连接/超时错误进入恢复流程；像素或协议不一致、非法掩码、存档错误等不自动重试，更不会发送确认。30 秒是再次发起请求的时间窗口；已经发起的单次同步请求仍受原有超时限制，不能保证在精确 30.000 秒结束。用户暂停会取消待执行的重试和待执行的人工抓拍；已经开始的传输可以完成。

## 改进二：确认失败不会误抓下一张

一次可靠留图分三步：接收并验证完整图像 → 原图、掩码及数据库持久保存 → 向板端确认相同启动号/事件号。只有确认才能释放对应 DDR 槽。

如果板端已经处理确认，但回复在网络中丢失，电脑无法立即知道板端是否释放。此时本版记住待确认身份，重试同一个确认，而不重新取下一张图。板端对同一启动号/事件号的重复确认可安全接受。确认成功后若只是状态读取失败，也只重试状态读取，避免重复存图。损坏帧不保存也不确认。启动号改变后的未决确认仍会安全停止，自动处理板端重启留待下一版。

## 改进三：画面、编号和存储同步

原图和掩码通过不同 HTTP 请求加载。现在必须两张都加载完、并且仍属于最新请求，才同时提交画面、红框、产品号和帧号；迟到的旧请求不能覆盖新图，旧请求失败也不会清除新请求的状态。

暂停、连接错误或超过 2 秒未更新时，预览标注“保留画面 · 非当前实时”。产品最佳证据帧与实时抽样帧分别标注。时间文字明确表示主机接收时间，不冒充相机曝光时间；队列证据仍可能早于当前 HDMI 画面，本版没有硬件时间同步。

存档容量原先只在进程启动时统计一次。独立测试/导入进程写入 SQLite 后，工作站现在通过 PRAGMA data_version 发现数据库变化并重算图片字节，避免界面容量低估。它不是多写入者的分布式配额锁；正常使用仍只运行一个工作站写入服务。

## 实板故障注入结果

测试图像确实经过 HDMI 输入、FPGA、DDR 和开发板以太网；仅在电脑本机增加测试 TCP 转发器，按计划截断或修改测试连接。没有改变网卡设置，也没有阻断其他网络。

| 故障场景 | 用时秒 | 保存记录数 | 结果 |
|---|---:|---:|---|
'''+ '\n'.join(rows)+f'''

部分图像中断后重取的全部图像字节和描述信息一致。确认回复丢失的实际请求顺序为“取图、确认、再次确认、状态”，只取一次图、只留一次证据。非法掩码的场景只发取图请求，没有确认；之后直接从开发板重新读取原事件验证有效，再显式确认。整个故障窗口采集间隙、无效帧、队列丢失和确认错误计数均无新增。

这是软件注入的连接故障，不能替代拔网线、掉电、交换机故障测试；长时断线继续经过大量瓷砖时，12 个待确认事件的板端队列仍可能满。测试长断线使用静态输入，不能据此声称无限期不丢生产事件。

连续验收窗口之后进行界面检查时，先切换了运动源，电脑仍暂停接收约 107 秒，恢复后观察到累计 6 个队列满丢失。已保留界面告警和计数，没有清零掩盖。这不属于上表/下节的无新增丢失计时窗口，但直接证明长暂停仍会丢事件。下一步需要明确“仅暂停显示”和“停止接收”的区别，并改善无头连续接收和重启恢复。

## 完整工作站连续测试

本次直接运行正式 Station 工作线程、HTTP API、PNG 保存与 SQLite 确认流程，不仅测试底层 TCP 类。真实照片连续移动 {c['seconds']:.2f} 秒，主机完成 {c['host_captures']} 次接收，自动保存 {c['saved']} 张缺陷最佳证据。所有证据均完整入镜，产品号无重复，掩码每个像素、区域框和面积与独立参考一致；采集间隙、损坏帧、队列丢弃与确认错误无新增。图片容量与实际文件字节一致。

另逐张通过输入条码还原物理来源：10 张属于 10 个不同的真实裂纹瓷砖经过，没有观察到的裂纹漏存和正常瓷砖误留，最大中心偏差 {identity['max_center_error_px']} 像素。运行结束恢复只预览模式，1 GiB 存档上限保留。照片属于既有真实数据集的连续运动回放，不能当作新独立检测准确率实验。

## 软件测试与发现的问题

75 项回归最终通过。新覆盖恢复等待、确认丢失、状态失败、暂停发生在传输中、暂停取消人工重试、恢复超时、损坏数据不重试、磁盘失败不确认、容量跨连接刷新等情况。

扩展回归曾发现拒绝跨来源 HTTP 请求时，Windows 偶尔报连接被中止而不是收到 403。处理程序现在先在 2 秒上限内读完最多 8192 字节的短请求体，再返回拒绝；来源验证仍阻止任何操作。失败日志保留，修改后全部重跑通过。

V1.8 已验证的压缩及 FPGA 算法未改动，本版不重新声称 50 对压缩性能实验；旧版实测数据明确作为基线引用。硬件时序也沿用 V1.6，未重复声称综合和布局布线。

## 使用与下一步

下载 .sdk/program_ethernet.bat，运行根目录“启动以太网工作站.bat”。工作区为 .sdk。网络短时中断无需立刻重启工作站；观察恢复状态即可。超过恢复窗口先检查连接，再点击开始；损坏数据或保存失败则先检查具体错误。人工暂停不会关闭 FPGA 采集，长时暂停仍需注意板端队列。

下一步继续完善启动号变化后的恢复、硬件帧时间及旧证据年龄标记，并评估在 FPGA 中生成完整图像 CRC，覆盖目前掩码/坐标检查不能发现的纯 RGB 损坏。同时保留弱裂纹召回率、跨材质误报、高速居中 40 像素、HDMI 上一帧框滞后和既有 CDC 端点的限制，不将网络可靠性提升描述成检测精度提升。
'''
(R/'docs/Tile_V1.9_可靠接收与同步报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.9

V1.8 自适应无损传输 + 30 秒有界恢复、确认重试、图像编号同步和存档容量刷新。

- Vivado：pynq_z2_tile_v1_53.xpr；Vitis 工作区：pynq_z2_tile_v1_53.sdk。
- 下载：.sdk/program_ethernet.bat；运行：“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.9_可靠接收与同步报告.md。
- 实板测试：scripts/board_v19_recovery.py、board_v19_station.py。
- 日志：reports/v132；内容与备份哈希：DELIVERY_MANIFEST.json。
- 默认仅预览，1 GiB 容量上限；旧 V1.8 保留且另有 ZIP 备份。

故障测试为本地 TCP 注入，不声称已通过物理断线、掉电或无限期无丢失；检测能力沿用 V1.6。
''',encoding='utf-8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.9 · 可靠性验证</title><style>body{margin:0;background:#edf4f4;color:#173e47;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1080px;margin:auto;padding:30px}a{color:#087d80}section{background:white;padding:24px;border-radius:18px;margin:20px 0}strong{font-size:28px;color:#087d80}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #dde7e8}.warning{border-left:5px solid #c87643;background:#fff3e9}</style><main><a href="/">← 返回工作台</a><p>V1.9 / 开发板真实图像 · 本地连接故障注入</p><h1>断线会恢复，证据不重复确认</h1><section><strong>5 / 5 实板故障场景通过</strong><p>75 项软件回归 · 连续运动保存 10 张完整证据 · 图像、红框和帧号一起显示</p></section><section><h2>故障验证结果</h2><table><tr><th>场景</th><th>秒</th><th>留图</th><th>结果</th></tr>'''+''.join(web)+'''</table></section><section class="warning"><h2>可靠性边界</h2><p>异常数据不确认；确认回复丢失时只重试同一事件。暂停取消后续重试。板端队列有限，长时间离线仍可能丢失。</p><p>本机代理测试不等于拔线、掉电验收。图像与算法沿用 V1.6，传输效率沿用 V1.8；工业准确率和高速居中仍需改进。</p><a href="/api/benchmark">完整验证数据 JSON</a></section></main></html>'''
page=page.replace('断线会恢复，证据不重复确认','断线后续传，截图不重复保存')
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.9 report, README and validation page generated')
