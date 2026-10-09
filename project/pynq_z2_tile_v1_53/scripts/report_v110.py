from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=read(R/'reports/v132/background_summary.json');assert s['passed']
s.update(version='V1.10',unit_tests=84,hardware='V1.6 unchanged')
(R/'reports/v132/background_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
doc=f'''# Tile V1.10 后台事件接收与低流量预览报告

## 交付与备份

本版从已验证的 V1.9 独立复制。旧目录完整保留，另有 `_baseline_backups/tile_v1_9_before_v1_10.zip` 源码和下载文件备份，SHA-256 记录于 ITERATION_PLAN.json 和 DELIVERY_MANIFEST.json。Vivado 工程重新建立，BIT/XSA/LTX 沿用 V1.6 已验证硬件；Vitis 平台、BSP 和本版 ELF 重新构建、实际下载。并未重新综合硬件，也没有提高时钟。

## 为什么修改

V1.9 连续测试无新增丢失，但后来界面检查期间停止接收约 107 秒、输入仍运动，12 个事件缓存装满并丢失 6 个事件。这个真实问题已保留在 V1.9 报告。看清一张图不应要求停止接收生产事件。

本版将“冻结预览”和“停止接收”分成两个明确操作。冻结时浏览器保留当前图像、掩码、红框、产品号及帧号，后台继续处理新事件；状态计数和事件列表仍更新。恢复预览重新加载最新可用图。停止接收才真正停止电脑取图，FPGA 仍运行，长时间停止仍可能耗尽板端缓存。

## 各部分职责

FPGA 保持 720p60 的暗谷、弱裂纹支持、区域框、产品身份和最佳帧选择逻辑。Vitis/ARM 保持 DMA、DDR 缓存、无损传输及确认，本版增加 op=5 参数命令，只更新请求阈值与弱裂纹开关，不发起抓拍；实际参数仍在产品间隙提交。电脑冻结时先查询少量状态，队列为空则约 200 ms 后重查，存在事件才取完整证据。没有把视觉识别移到电脑。

生产者/消费者思路：FPGA 产生事件，DDR 队列保存事件，电脑消费并确认。冻结只是暂停显示这个消费者的一个输出，不停止接收消费者本身。每张图仍须通过既有验证、按照存储模式处理后才能确认。

## 实板验证

84 项软件回归通过，包含冻结时无事件不抓图、有事件处理及确认、冻结中的手工板端抓拍、恢复预览与停止接收的区别、参数更新、网络故障恢复及请求边界。板端 op=5 在阈值 123/关闭增强和 89/开启增强两种组合下，实际配置正确，抓拍请求号及队列头尾均不变化。

| 模式 | 实测秒 | TCP 应用接收字节 | 完整帧接收 | 缺陷留图 |
|---|---:|---:|---:|---:|
| 正常预览 | {s['normal']['seconds']:.3f} | {s['normal']['received_bytes']:,} | {s['normal']['captures']} | {s['normal']['saved']} |
| 冻结、后台接收 | {s['frozen']['seconds']:.3f} | {s['frozen']['received_bytes']:,} | {s['frozen']['captures']} | {s['frozen']['saved']} |

每秒接收字节减少 **{s['received_rate_reduction_percent']:.3f}%**。这是相同循环运动素材的两个不同长度时间窗口，包含状态和确认响应，不包含 TCP/IP、以太网头。不能解读成提高了检测精度或电脑预览达到 60 fps。冻结窗口经过 20 块产品，10 块缺陷全部留存，恰好只取 10 张图，无空闲预览整帧；正常窗口经过 8 块产品，留存 4 张缺陷。

14 张证据逐张核对完整入镜、独立输入条码、唯一产品号、正常/裂纹来源、中心误差不超过 32 像素，以及每个掩码像素、区域框和区域面积与参考一致。两窗口采集间隙、无效采集、队列满丢失及确认错误均无新增。材料仍是已有真实照片的连续移动回放，不是新独立盲测。

另通过浏览器确认冻结后的帧键不变而后台接收次数增长。截图和前后 DOM 值保存在 reports/v132。报告页展示本版实际测试数值。

第一次自动验收脚本在板端状态尚未返回时把 None 当字典，测试在准备阶段退出；修正等待条件后完整重跑，原失败日志保留。没有把这一脚本错误算作硬件失败，也未删除失败记录。

## 操作和容量

使用 `.sdk/program_ethernet.bat` 下载，根目录“启动以太网工作站.bat”打开软件。Vitis workspace 就是同名 `.sdk`。若只想仔细看当前图，点击“冻结预览”；若确实要停止电脑接收，点击“停止接收”。“板端抓拍”请求待取事件或新采样帧，不能当作保存当前冻结画面。

冻结模式尊重存储设置：“自动留图”保存新缺陷；“仅预览”仍接收和确认，但不自动保存。完成测试恢复仅预览和 1 GiB 存档上限，避免无人操作时不断增加磁盘用量。服务重启后的计数从新会话开始；已有 14 张验收图片保留。

## 已知限制与下一步

冻结节流效果取决于缺陷事件密度；每块产品都出缺陷时收益会变小。停止服务、持续断线或电源中断仍可能丢事件；有限队列无法保证无限期保存。当前网络完整性包含协议、掩码和区域一致性检查，但纯 RGB 字节损坏可能逃过这些检查，因此下一版优先在 FPGA 生成完整像素 CRC，再由电脑解压后比较，拒收不一致帧。

弱裂纹召回、跨材质误报、高速最佳帧最多 40 像素中心偏差、HDMI 使用前一帧红框及既有五个 CDC 端点限制仍保留。本版没有修改它们，也不把传输优化说成工业准确率验收。
'''
(R/'docs/Tile_V1.10_后台事件接收报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.10

冻结预览仍继续接收事件；空队列只轮询状态。实板接收字节率减少 97.69%，10 个缺陷完整留图，84 项软件测试通过。

- Vivado：pynq_z2_tile_v1_53.xpr；Vitis：pynq_z2_tile_v1_53.sdk。
- 下载：.sdk/program_ethernet.bat；打开：“启动以太网工作站.bat”。
- 完整报告：docs/Tile_V1.10_后台事件接收报告.md。
- 实板复现：scripts/board_v110_background.py；证据：reports/v132。
- 默认仅预览、1 GiB 上限。旧 V1.9 保留并另有 ZIP。

FPGA 图像算法与硬件沿用 V1.6；本版修改 Vitis 传输控制和电脑接收。冻结与停止接收不同，长时停止仍可能丢事件。
''',encoding='utf-8')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.10 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:36px;color:#087d80}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #dde7e8}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.10 / 开发板真实输入 · 独立保存旧工程</p><h1>画面冻结，缺陷接收继续</h1><section><strong>接收字节率减少 {s['received_rate_reduction_percent']:.2f}%</strong><p>冻结 60 秒窗口：20 块产品，10 张缺陷证据完整保存。空闲时不传整帧。</p></section><section><h2>实测对比</h2><table><tr><th>模式</th><th>窗口秒</th><th>接收字节</th><th>完整帧</th><th>缺陷图</th></tr><tr><td>正常预览</td><td>24.547</td><td>185,275,238</td><td>209</td><td>4</td></tr><tr><td>冻结后台接收</td><td>60.609</td><td>10,587,832</td><td>10</td><td>10</td></tr></table><p>84 项软件回归通过。14 张图的掩码、区域、物理来源、完整入镜和居中检查通过。计时窗口无新增队列丢失、无效帧或采集间隙。</p></section><section class="warning"><h2>理解测试范围</h2><p>统计 TCP 应用字节，含状态和确认，不含网络头。不同长度窗口使用同一循环素材；不代表检测精度提升或 60 fps 电脑预览。</p><p>冻结尊重存储模式。停止接收仍可能使 12 个事件缓存耗尽。硬件沿用 V1.6，下一版增加整帧 CRC。</p><a href="/api/benchmark">实际验收数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.10 report generated')
