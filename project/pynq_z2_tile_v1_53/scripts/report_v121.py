from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
n=read(O/'dma_recovery_native.json');h=read(O/'health_native.json');w=read(O/'dma_recovery_board/summary.json');fw=read(O/'firmware_audit.json')
t=read(O/'transport_comparison.json');f=read(O/'recovery/summary.json');r=read(O/'restart/summary.json')
c=read(O/'station_continuous.json');a=read(O/'station_identity_audit.json');b=read(O/'background_summary.json');ui=read(O/'ui_restart_after.json')
dc=read(O/'descriptor_native.json');sc=read(O/'firmware_crc_test.json');sg=read(O/'native_sg/result.json')
player=read(O/'player_lock.json');assert player['passed'] and w['cleanup_resumed']['resumed_successfully']
assert all(v['passed'] for v in (n,h,w,fw,t,f,r,c,a,b,ui,dc,sc)) and sg['result']=='PASS'
units=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 152 tests' in units and units.rstrip().endswith('OK')
assert all(x['independent_process_reload_passed'] for x in w['cases'])
assert all(e['recovery_generation']==0 for e in c['records'])
summary=dict(version='V1.21',passed=True,firmware=fw,recovery_native=n,health_native=h,recovery_board=w,unit_tests=152,transport=t['summary'],faults=f,restarts=r,ui_restart=ui,
 station=dict(seconds=c['seconds'],captures=c['host_captures'],saved=c['saved'],identity=a),background=b,player_lock=player,hardware_origin='Unchanged V1.15 BIT/XSA/LTX; V1.20 bounded recovery retained; per-event generation added')
(O/'generation_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f} |" for name,v in t['summary'].items())
fault_rows='\n'.join(f"| {v['number']} | {v['retained_generation']} | {v.get('mid_product',{}).get('generation','无新图')} | {v.get('next_product',{}).get('generation','无新图')} | {v['after']['capture_recovery']['state']} | {v['after']['capture_recovery']['last_duration_ms']} |" for v in w['cases'])
doc=f'''# Tile V1.21 每帧恢复代次与证据同步报告

## 本版交付

每张图像现在携带固定的采集恢复代次。恢复前排队的旧截图保持旧代次，恢复后新采到的图使用新代次。最佳帧发布、网络重传、保存、电脑程序重启、待确认恢复和 CSV/JSON 导出都保留这个身份字段。旧记录明确显示未知，不伪造代次 0。

本版是 V1.20 有界 DMA 恢复的单项同步增量，FPGA 检测算法、时钟和下载 BIT 不变。没有用这一版宣称裂纹识别准确率进一步提高。

## 保存、构建与责任划分

- 旧工程 D:/Vivado/pynq_z2_tile_v1_20 完整保留。
- 新工程 D:/Vivado/pynq_z2_tile_v1_53；同名 .xpr 为 Vivado 工程，同名 .sdk 为 Vitis workspace。
- 备份 D:/Vivado/_baseline_backups/tile_v1_20_before_v1_21.zip，SHA256 5bc5ba04d86bc9aa376b0d2ae2017769b43567ebf9025199638fb7daaddce581。
- Vivado 重新建立可打开的工程结构，继承已验收 V1.15 BIT/XSA/LTX；不重复声称本版有新的布局布线、频率或时序测量。
- Vitis 完整构建平台和应用，ELF SHA256 {fw['elf_sha256']}。text 131614 B、data 3476 B、bss 7435728 B，相比 V1.20 仅 text 增加 16 B。审计实际中断浮点保存/恢复、4 KiB IRQ 栈、整数 memcpy、作者/导入源码一致性及旧 ACK 路径。

FPGA 仍按 720p60 进行像素检测、区域和产品/最佳帧判定、CRC。ARM 按 PL 标志管理最佳图内存引用和事件发布，处理 DMA、压缩、网络与恢复；新增的只是证据身份管理，不在 ARM 上识别图像。电脑负责显示、校验、存档与人工复核。

## 实现内容与公式

ARM 验证原始 PL 描述 CRC 后，在事件描述第 8 字写入 `(generation << 8) | reason`。低 8 位保持事件原因，高 24 位保存代次。当前成功恢复最多 3 次，所以本版只接受代次 0～3、原因 1～3。非法值不入库、不确认。

代次在消费该张有效帧时绑定，不能读取取图时的最新计数代替。最佳帧完成发布时只修改原因低位，保留被选像素帧的代次。网络响应仍为 276 B，图像格式不变，没有增加每次图像传输字节。

0 表示本次启动尚未成功恢复；1～3 表示对应次数的恢复之后，必须结合 boot_id 使用。失败不产生新代次。恢复计数不是缺陷严重程度，也不是所有漏检产品的数量。

存档重复写入时，若同一证据身份出现不同代次就拒绝，原图及人工意见保留。待确认日志也比较代次；进程重启后从磁盘重新核对。旧日志缺字段与显式空值兼容，未知不会冒充已知代次。

## 实板验证

| 故障次数 | 保留旧图代次 | 恢复后抽样代次 | 下一产品证据代次 | 最终状态 | 恢复阶段 ms |
|---:|---:|---:|---:|---|---:|
{fault_rows}

每次注入前固定一张未确认图。守卫脚本核对版本、启动号、事件与次数后清除 DMA Run/Stop；不写像素、描述和队列。恢复后以 RAW/RLE 重读，旧图像和描述逐字节相同，三类 CRC 通过，代次仍为原值。前三次新增手动/实时图和下一件产品图的代次递增；旧产品 EXIT 不发布被中断最佳帧。

每个故障用独立小存档保存证据，真正启动另一个 Python 进程重读 SQLite、PNG 和待确认记录，验证代次从磁盘恢复。故意把同一证据改成另一代次的保存请求被拒绝。完成确认后再次用独立进程核对记录和确认历史，第四次超过恢复上限时旧图仍可取回，但没有新图。

这是实际开发板可控 DMA 停止试验，不是物理 HDMI 拔插或断电试验。恢复耗时仅指固件状态机阶段，不含网页刷新；故障期间帧间隙和无效包在原始 JSON 中保留。故障试验后重新下载干净固件，正常回归与诊断计数分开记录。

首次运行四个故障场景均通过，但清理阶段电脑 WPF 播放器因读取 display_command.txt 遇到 Windows 文件共享冲突而退出，未完成干净重载，因此最初脚本整体失败。原始错误日志和四个成功场景证据均保留，没有将首次运行冒充完整通过。

修复为仅在命令读取遇到 IOException 时跳过一个 20 ms 定时器回调，下次重读，播放器继续渲染。实际独占命令文件 {player['exclusive_lock_ms']} ms，进程存活、遥测更新，仍渲染 {player['rendered_frames_during_lock']} 帧；释放后成功切换空传送带。随后单独执行清理恢复脚本并实测新启动采集正常。该附带修复只涉及电脑测试源，不改 FPGA 或 DMA 固件。

## 自动化与正常回归

152 项主机测试通过，包括 12 组原因/代次组合、旧协议未知值、保留位拒绝、相同证据冲突、日志重启、旧日志兼容、头 CRC 保护代次及真实 HTTP CSV/JSON 导出。实际 C 编译的 20 个场景覆盖 V1.20 原有恢复与槽保护，以及 0～3 代的最佳图延迟发布、两类抽样原因。健康监测边界/随机、3000 组 CRC 对照、1280 个描述单比特错误、48 槽所有权回归也通过。

50 对同事件 RAW/RLE 图逐字节相同，9 类网络故障、3 类重启与 UI 待确认恢复通过。UI 继续原事件只做 stats/ACK/stats，零新取图，原 PNG 不变。

| 输入 | RAW 请求中位 ms | 自适应请求中位 ms | 图像体减少 % |
|---|---:|---:|---:|
{rows}

连续运动 {c['seconds']:.3f} 秒，收到 {c['host_captures']} 张电脑预览/事件图，10 件预期缺陷产品全部保存；最大居中偏差 {a['max_center_error_px']} 像素，来源身份、独立参考掩码、区域框和面积一致，所有正常留图代次为 0。正常窗口没有新增间隙、无效包、队列丢弃、确认或描述 CRC 错误。

冻结预览仍保留事件接收，应用层接收字节率减少 {b['received_rate_reduction_percent']:.3f}%，10 件事件全保存。它不是链路极限吞吐量或 60 fps 电脑预览测量。结束保持仅预览、1 GiB 上限和真实照片连续运动，避免无人值守自动堆积图片。

## 如何操作与答辩

使用本版 .sdk/program_ethernet.bat 下载，再启动本版工作站。连接方式仍为电脑 HDMI → PYNQ-Z2 HDMI IN，板 HDMI OUT → 显示器；PROG UART USB 接电脑，板网口直连电脑。HDMI 输入为 1280×720、60 Hz。

复核窗口增加“采集恢复代次”。例如网页实时状态已成功恢复 1 次，而某条旧图显示代次 0，是合理的：它在故障前采到、恢复后才被取回。不要为了让两者看起来相同而修改旧记录。

回退先停止当前接收程序与播放器，再用 V1.20 自己的 BIT/ELF 和工作站；不要交叉混用版本。旧工作站没有解析本版事件原因字段高位的代码，不能接收恢复后的 V1.21 事件；新工作站能将旧版代次显示为未知。故障注入脚本仅供维护测试。原理、位运算与编号含义详见 V1.21_采集代次原理.md。

## 优势、剩余问题与下一步

优势是传输不增量而证据更可追溯；恢复、晚到截图和重启确认不会把当前状态错误套到历史图。CRC、帧号、产品号和代次各司其职，便于竞赛展示实际闭环。

剩余限制包括弱裂纹种子依赖、跨材料误报、缺少独立相机数据、高速居中偏差、HDMI 前一帧框、既有 CDC、有限 12 项队列、掉电丢失未存 DDR、完整长期身份周期和中断最坏栈验证。PNG 与 SQLite 仍不是跨文件原子事务，系统仍按单接收端设计。代次不补回丢帧，也不证明检测精度；CRC 不是认证机制。

下一步先修复“暂停/停止接收”与正在进行的状态请求之间的竞争。本版代码的独立本地受控桥审计已复现：状态请求尚未返回时点击暂停，随后状态正常返回，仍会启动一次新的 capture，再 ACK 和读取状态；没有连接硬件，证据为 pause_race_audit.json。这是本版明确保留的下一项限制，不能声称停止操作已完全同步。之后再考虑更大的物理 HDMI 恢复范围与真实材料盲测。继续一版一验收，保留回退入口。
'''
(R/'docs/Tile_V1.21_采集恢复代次与证据同步报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.21

把采集恢复代次绑定到每张图，保持旧排队证据代次，恢复后新图递增；存档、确认恢复与导出保留该字段，网络字节数不增加。

- Vivado：pynq_z2_tile_v1_53.xpr；Vitis workspace：pynq_z2_tile_v1_53.sdk。
- 构建：.sdk/build_ethernet.py；下载：.sdk/program_ethernet.bat；启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.21_采集恢复代次与证据同步报告.md；学习：docs/V1.21_采集代次原理.md。
- V1.20 原工程和 ZIP 均保留。FPGA 沿用 V1.15，无新时序或检测精度结论。
- stop_dma_v121.tcl 为维护故障注入工具，日常演示不要运行。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.21 验证</title><style>body{{margin:0;background:#edf4f4;color:#173e47;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1000px;margin:auto;padding:30px}}a{{color:#087d80}}section{{background:white;padding:24px;border-radius:18px;margin:20px 0}}strong{{font-size:29px;color:#087d80}}.warning{{border-left:5px solid #c87643;background:#fff3e9}}</style><main><a href="/">← 返回工作台</a><p>V1.21 / 证据同步</p><h1>旧图保留原代次，新图标明恢复来源</h1><section><strong>每帧绑定 · 不增加传输字节</strong><p>实板三次恢复，旧图分别保留 0 / 1 / 2 代，新图进入 1 / 2 / 3 代。第四次故障按上限停止，旧证据仍可读。</p></section><section><h2>从采集到落盘重启均已检查</h2><p>152 项主机测试、20 个实际 C 场景；独立进程重读截图、待确认记录和确认历史。50 对图像、9 类网络故障、3 类重启与连续产品回归通过。</p><p>居中偏差最大 {a['max_center_error_px']} 像素；冻结预览字节率减少 {b['received_rate_reduction_percent']:.2f}%。</p></section><section class="warning"><h2>明确的验证边界</h2><p>真实照片合成运动与可控 DMA 停止；不等同物理 HDMI 插拔、断电或工厂识别精度。旧记录显示“未记录”，不冒充代次 0。</p><a href="/api/benchmark">完整实测 JSON</a></section></main></html>''',encoding='utf-8')
print('V1.21 report generated from passing fresh evidence')
