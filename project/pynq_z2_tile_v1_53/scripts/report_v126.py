"""Publish only measured, passed V1.26 evidence; never synthesize test results."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_25'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={'firmware':'firmware_audit.json','gem_ownership':'gem_ownership_audit.json','native':'native_packed/result.json','stream_native':'native_stream/result.json','invalid_requests':'invalid_modes_board.json','legacy_client':'legacy_client.json','transport':'transport_comparison.json','faults':'recovery/summary.json','packed_faults':'packed_faults.json','noncanonical':'noncanonical/summary.json','restarts':'restart/summary.json','station':'station_continuous.json','identity':'station_identity_audit.json','background':'background_summary.json','health_native':'health_native.json','recovery_native':'dma_recovery_native.json','ui':'wire_mode_ui.json'}
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
log=(O/'host_tests.log').read_text(encoding='utf-8-sig');assert 'Ran 198 tests' in log and log.rstrip().endswith('OK')
W=R/(R.name+'.sdk')
for name,h in s['stream_native']['source_sha256'].items():assert h==sha(W/'ethernet_sources'/name)
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json')
summary=dict(version='V1.26',passed=True,unit_tests=198,default_policy='LEGACY_ADAPTIVE_RLE_RAW',new_policy='OPTIONAL_STREAMING_PACK25',**s,
 baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Detection hardware unchanged; prior accuracy results are not new blind tests'),limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
t=s['transport']['summary'];n=t['transport_noise'];station=s['station'];old=prior['validation']['transport']['summary']['transport_noise']
gain=100*(1-n['compact']['request_ms']/old['compact']['request_ms'])
rows='\n'.join(f"| {k} | {v['raw']['request_ms']:.3f} | {v['legacy']['request_ms']:.3f} | {v['compact']['request_ms']:.3f} | {v['compact']['wire_payload_bytes']:.0f} | {v['compact']['wire_saving_percent']:.4f}% |" for k,v in t.items())
doc=f'''# Tile V1.26 分块编码与发送重叠实板报告

## 做成了什么

本版改进可选的 PACK25 无损传输：ARM 不必先把整张图编码完才开始网络发送，已经完成的颜色前缀可以先发送。FPGA 仍负责 720p60 裂纹候选检测、红框区域、产品跟踪、最佳证据选择和原始 CRC；Vitis 程序管理 DMA、队列、帧槽、格式转换及 TCP；电脑负责显示、证据校验、存档和人工复核。视觉算法没有移到电脑或 ARM。

V1.25 省流 21.875%，但先整帧编码造成额外等待。本版保持包格式、时钟和采集架构不变，先试编码与发送重叠，再补上网卡 DMA 持有发送缓存的生命周期问题，最后处理 RAW 对齐搬运开销。三个阶段记录分别保留，最终数据包含全部修正。无新增整帧缓存；TCP 有界队列内增加数据副本，运行时堆占用可能上升。

## 实测结果

同一保留事件在 RAW32、旧自适应 RLE/RAW、可选 PACK25 三种方式下交替读取。50 组、150 次读图的原始 BGRM32 字节、帧描述和三个 CRC 一致。

| 输入 | RAW ms | 旧自适应 ms | 重叠省流 ms | 省流负载 B | 相对 RAW 减少 |
|---|---:|---:|---:|---:|---:|
{rows}

难压缩画面：V1.25 省流中位数 {old['compact']['request_ms']:.3f} ms，本版 {n['compact']['request_ms']:.3f} ms，跨版本测量下降 {gain:.2f}%。本版同轮旧自适应为 {n['legacy']['request_ms']:.3f} ms。两版在不同时间测量，系统负载可能不同，不能把跨版本差值全当作纯算法收益。本版省流头等待 {n['compact']['header_wait_ms']:.3f} ms，载荷接收 {n['compact']['payload_ms']:.3f} ms，主机解码 {n['compact']['decode_ms']:.3f} ms。

每帧颜色与掩码无损，仍由 3,686,400 B 变成 2,880,000 B，减少 806,400 B。本版两种自适应方式对噪声耗时基本相当，不用微小差异宣传明显提速。RAW 比 V1.25 的约 69 ms 变慢，代价来自补齐的数据生命周期保护；后续优化必须保持同等保护。以上是应用请求耗时和负载，不是网卡标称 1 Gbps，也不代表电脑预览 60 fps。默认维持原有兼容策略；用户可在“网口传输”选择省流，不再在界面把一种格式描述为必然更快。

## 调度及同步原理

一帧 N=921600 个像素，输入每像素 B、G、R、M 四字节。输出先放 3N 字节颜色，再放 ceil(N/8) 字节掩码。每轮最多编码 2048 像素。如果已完成 p 个像素，允许发送的总前缀只有 H+3p 字节，其中 H=276 为头长度。掩码区域在整个编码完成前不可发送，完成后上限才变为 H+3N+ceil(N/8)。

TCP 仍每 50 微秒至多入队两个 MSS（2920 字节），不在采集主循环中睡眠。编码只向前追加颜色，掩码暂时隐藏。最终固件对头和载荷都使用 TCP_WRITE_FLAG_COPY，把本轮完成的数据复制到协议栈自己的 pbuf 存储中；GEM 网卡 DMA 的引用会保留这份存储，即使 TCP 已经中止，也不会依赖应用下一次将复用的编码缓存。复制工作受同一个两 MSS 上限约束。原始事件槽仍由队列保留，只有应用层确认才释放。

初版仅假定 tcp_abort 后所有引用均已释放。复核本机 AMD xemacpsif_dma.c 发现，驱动把 q->payload 地址放入 TX 描述符，并调用 pbuf_ref(q)，直到发送完成才释放，因此这个假定不足。扩展实际 network.c 的本机测试，模拟网卡在 abort 后仍持有引用，重连确认旧事件后编码下一事件，复现旧缓存内容被改写。修正后 {s['stream_native']['gem_retained_reference_checks']} 次保留引用检查通过，{s['stream_native']['copied_payload_writes']} 次载荷提交均复制，借用应用载荷指针为零。反例、旧 ELF、首轮测速和旧测试存档完整保留在 reports/v132_nocopy_trial。没有声称在实板上人为卡死过 GEM DMA。

直接 COPY 不缓存 DDR 的第二阶段测速，RAW 约 277 ms，暴露未对齐字节访问的高开销。最终版 RAW 先用整数 burst memcpy 搬到已有对齐 input_chunk，再交给协议栈复制。每次仍最多 2920 字节，RAW 分块按 4 字节对齐；不足 4 字节的剩余发送缓存等确认释放后继续。最终表格来自再次构建、下载和测速。第二阶段原始数据及 ELF 保留在 reports/v132_copy_unstaged_trial，不以较快旧试验冒充最终结果。

如果源数据出现非法掩码高位，已发出头或半张图后不能突然改成 RAW。因此立即中断连接，并按启动号、事件号、帧号、槽地址和原 CRC 记住这一个失败事件。重读它使用 RAW32，完整保留错误位，由电脑检查原始 PL CRC 并拒绝。新事件清除旧失败记录。不是“把错误位删掉后继续传”。

## 一步一步的验证

1. 实际 network.c 编译为本机隔离测试程序，模拟 TCP 延迟确认、发送窗口压力、ERR_MEM、部分发送、断线和 GEM 延迟释放；完成 {s['stream_native']['roundtrips']} 次完整往返、3 次部分发送重试，以及早/晚非法位中断。先复现反例再修复，并以新固件重新做后续实板测试。这不是物理以太网吞吐测试。
2. 实际 C 编码器 294 组往返、574 个容量/对齐边界、840 个非法高位拒绝；主机 198 项测试通过。18 个健康边界、25000 随机操作、20 个实际 main.c 恢复场景通过。
3. 建立可打开的 Vivado 工程，完整构建 Vitis 平台/BSP/ELF，反汇编检查中断浮点上下文、4096 字节 IRQ 栈、整数 memcpy。下载 BIT/ELF 后核对固件 0x11a00。
4. 实板 50 组三种格式对照、中途断线同事件重取、20 类非法请求及未修改 V1.24 客户端兼容测试通过。
5. 9 类网络故障加 4 类 PACK25 故障通过；损坏证据不保存、不确认；确认回复丢失不重复存图。网络故障由本地代理注入，不冒称拔网线。
6. JTAG 在真实锁定 DDR 图像的像素 100 和 800000 分别翻转非法位：第一种在发头前中止，第二种已发出部分图像后中止。随后 RAW 完整保留该位，电脑 CRC 拒绝；还原后同事件通过 RAW 确认，下一事件恢复 PACK25。原始错误日志与结果见 noncanonical。
7. 3 类保存后重启：确认前进程退出、确认后退出、待确认时实际 JTAG 重下板。原 PNG 和人工备注保留，恢复不重新截图。此项不等于物理掉电。
8. 连续运动 {station['seconds']:.3f} 秒，主机抽样 {station['host_captures']} 张，保存 {station['saved']} 个缺陷产品各一张最佳图，最大居中偏差 {s['identity']['max_center_error_px']} 像素。掩码、框、区域面积与参考一致，无新增 gap、invalid、drop、ACK 或描述 CRC 错误。
9. 冻结预览后后台仍接收事件，收到的应用字节率下降 {s['background']['received_rate_reduction_percent']:.3f}%；这是已有功能回归。界面实际切换两种传输模式后，收到的格式、字节和 CRC 对应，完整 PNG 相同，未增加存档。

一次紧接 JTAG 下载的取状态请求报主机不可达，尚未开始读图；稍后同一固件正常响应。失败日志保留为 startup_connect_failure.log，未把它改成成功记录。增加 wait_board_ready.py 的有界启动检查，核对已下载启动号、固件版本和完整帧健康状态后才开始测速；不凭下载命令返回就假设网口立即可用。

## 工程、备份和操作

工程：{R.as_posix()}；Vivado：{R.name}.xpr；Vitis workspace：{R.name}.sdk。BIT、XSA、LTX 逐字节继承 V1.24，未重新声称完整综合实现。时序与 CDC 限制继承原报告。ELF SHA256：{s['firmware']['elf_sha256']}。

前版原工程完整保留 {B.as_posix()}。轻量备份：{plan['backup']}；SHA256：{plan['backup_sha256']}。ZIP 包含源码、文档及关键下载产物；大量运行素材仍在原工程，不把轻量包当作全数据备份。

电脑 HDMI 接 PYNQ-Z2 IN，OUT 接显示器，USB 接 PROG UART，网线直连电脑，1280×720 60 Hz。停止旧工作站后，从本版 .sdk/program_ethernet.bat 下载，再启动 host/start_station.ps1。默认仅预览，归档上限 1 GiB；测试自动留图有时间边界，不持续无限落盘。

## 局限及下一步

检测硬件未改变。V1.24 的同材质弱裂纹改善、跨材质误报仍然适用；旧照片是开发集，本版没有新的盲测准确率。尚未连接真实相机，曝光、运动模糊、产线振动仍待验收。五个已有 CDC 不安全端点、12 事件有限队列、未传出 DDR 数据掉电丢失、HDMI 前一帧框与电脑同帧框的差别仍需解决。

下一小版优先完善测试输入命令身份：相同素材连续请求或播放器重启时，仅靠文件修改时间与名字可能误判同步，需要命令唯一编号、播放器明确回报已采用编号，以及真实文件争用和重启测试。之后再单独评估网络泵预算或硬件传输优化，不能同时叠加未经量化的改动。真实材料测试和可靠性指标各自报告，不用省流比例代替检测效果。
'''
(R/'docs/Tile_V1.26_分块传输与同步实板报告.md').write_text(doc,encoding='utf-8')
print('Generated V1.26 report solely from passed evidence')
