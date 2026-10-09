from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_24'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={'firmware':'firmware_audit.json','native':'native_packed/result.json','invalid_requests':'invalid_modes_board.json','legacy_client':'legacy_client.json','transport':'transport_comparison.json','faults':'recovery/summary.json','packed_faults':'packed_faults.json','noncanonical':'noncanonical/summary.json','restarts':'restart/summary.json','station':'station_continuous.json','identity':'station_identity_audit.json','background':'background_summary.json','health_native':'health_native.json','recovery_native':'dma_recovery_native.json','ui':'wire_mode_ui.json'}
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
assert 'Ran 198 tests' in (O/'host_tests_final.log').read_text(encoding='utf-8-sig') and (O/'host_tests_final.log').read_text(encoding='utf-8-sig').rstrip().endswith('OK')
assert s['native']['header_sha256']==sha(R/(R.name+'.sdk')/'ethernet_sources/packed_pixels.h')
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json')
summary=dict(version='V1.25',passed=True,unit_tests=198,default_policy='LATENCY_ADAPTIVE_RLE_RAW',new_policy='OPTIONAL_BANDWIDTH_PACK25',**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Unchanged detection RTL, BIT, XSA and LTX; prior algorithm accuracy/material limits inherited, not new blind test'),limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
t=s['transport']['summary'];n=t['transport_noise'];station=s['station'];bg=s['background']
rows='\n'.join(f"| {k} | {v['raw']['request_ms']:.3f} | {v['legacy']['request_ms']:.3f} | {v['compact']['request_ms']:.3f} | {v['compact']['wire_payload_bytes']:.0f} | {v['compact']['wire_saving_percent']:.4f}% |" for k,v in t.items())
doc=f'''# Tile V1.25 无损位打包、传输取舍与实板报告

## 产品变化

本版在保留 V1.24 检测算法的基础上增加一种省流传输选项。FPGA 继续做 720p60 裂纹候选检测、区域框、产品跟踪、最佳截图和原始 CRC。Vitis/ARM 对被请求的帧进行无损格式转换、排队和网络传输，不执行视觉算法。电脑工作台支持延迟优先、省流优先、原始对照三种方式，并显示当前截图实际使用的编码、字节和校验状态。

用户目标是持续运动的产品检测和可审核证据。减少线上字节是本版的进步；默认采集延迟不能因此被悄悄牺牲。工程和测试都保留这个区分。

## 原理

原始像素是 B、G、R、M 四个字节，其中 M 只有 0/1。一帧 N=1280×720=921600 像素，原格式 4N=3686400 字节；紧凑格式 3N+ceil(N/8)=2880000 字节，精确减少 806400 字节、21.875%。颜色不降精度，掩码不丢像素。更多公式、位排列和缓存所有权说明见 V1.25_无损位打包原理.md。

ARM 复用已有输出缓存，每轮最多处理 2048 像素，然后返回采集与网络轮询。连续四像素打包为三个颜色字和四个掩码位，减少字节存储指令。编码完成前不会发出新的载荷，发送完成前不会改写缓存。客户端重建完整 BGRM32，再与 FPGA 原始 CRC 对比；响应头 CRC 同时保护帧号、产品号、配置、编码和长度。

旧客户端不声明 PACK25 能力，板端便只返回 RAW32/WORD_RLE。新客户端也只有从已校验响应确认固件支持后，才发送能力位。非法模式、非法长度和掩码填充位被拒绝。CRC 是检错，不是安全认证。

## 实测：省流不是提速

同一个板端保留事件以三种方式轮流读取，旋转测量顺序。50 组、150 次完整读图的原图、掩码、描述和 CRC 一致，最后才确认释放原事件。

| 输入 | RAW ms | 旧自适应 ms | 省流模式 ms | 省流载荷字节 | 相对 RAW 减少 |
|---|---:|---:|---:|---:|---:|
{rows}

难压缩画面在省流模式下减少 21.875% 负载，但中位请求耗时从 {n['legacy']['request_ms']:.3f} ms 增至 {n['compact']['request_ms']:.3f} ms。其中新模式头等待 {n['compact']['header_wait_ms']:.3f} ms，负载接收 {n['compact']['payload_ms']:.3f} ms，解码 {n['compact']['decode_ms']:.3f} ms。这些是本机端到端请求测量，不是纯物理以太网线速。

因此 **默认保留延迟优先的旧自适应方式**，省流优先是界面明确可选模式。对本来就能很好游程压缩的瓷砖照片，仍选 WORD_RLE，不强制用更大的位打包。首次探索数据保留为 transport_first_trial.json，最终数据为 transport_comparison.json，不隐藏增加延迟的结果。

## 本版逐步测试

- 198 项主机测试全部通过；新增协议能力协商、错误长度、颜色/掩码损坏、默认策略和配置切换快照测试。
- 实际 C 编码器 {s['native']['layout_roundtrips']} 组往返，{s['native']['capacity_alignment_rejections']} 次容量/对齐拒绝，{s['native']['noncanonical_rejections']} 个非法高位拒绝；包括完整 720p 与各种不对齐长度、不同分块预算及输出保护字。
- 实板 {len(s['invalid_requests']['cases'])} 类非法请求拒绝，配置、队列不变。未经修改的 V1.24 客户端在 V1.25 固件上通过真实 RAW/RLE 接收对照。
- 9 类既有网络故障回归，加 4 类 PACK25 专项：颜色位翻转、掩码位翻转、负载中断、确认响应丢失。损坏证据不保存不确认；中断后保留同一事件；确认丢回复不会重复存图。
- 实际 JTAG 修改当前锁定 DDR 帧中的一个非法掩码位：板端退回 RAW，完整保留非法位；电脑 CRC 拒绝；恢复原位后同一事件重新通过 PACK25 和 CRC，最后确认。没有把模拟数据冒充板端画面。
- 3 类真实重启测试都使用 PACK25 保存证据：程序保存后、确认前退出；确认后退出；有待确认记录时重新 JTAG 下载 BIT/ELF。恢复不重新截图，原 PNG 和人工备注保持不变。不是物理拔电测试。
- 60 秒持续运动和冻结预览后台回归：{station['host_captures']} 张主机采样，{station['saved']} 个缺陷产品各一张最佳图；最大居中偏差 {s['identity']['max_center_error_px']} 像素，全部掩码、框和区域面积与参考一致，无新增 gap/invalid/drop/ACK 错误。冻结后字节率下降 {bg['received_rate_reduction_percent']:.3f}%。
- 18 项采集健康边界、25000 随机操作、20 个实际 main.c 恢复/槽位场景重新通过；固件反汇编确认整数 memcpy、浮点中断上下文保护与 4096 字节 IRQ 栈仍在。

## 工程、构建与回退

目录 {R.as_posix()}；Vivado 工程 {R.name}.xpr；Vitis workspace {R.name}.sdk。本版准备可打开的 Vivado 工程，直接复用 V1.24 已通过时序的 BIT/XSA/LTX，三者逐字节一致；没有假称重新综合了新硬件。Vitis 平台与应用完整构建，ELF SHA256 {s['firmware']['elf_sha256']}。板端固件版本 0x11900，下载记录见 reports/programmed_v132.json。

前版完整原工程保留在 {B.as_posix()}。轻量备份 {plan['backup']}，SHA256 {plan['backup_sha256']}；源码哈希复核后才建立新目录。该 ZIP 包含源码、文档和关键下载文件，完整实验原图仍保留在原工程。

运行方式与前版相同：电脑 HDMI→板 IN，板 OUT→显示器，USB PROG UART 与直连网线；1280×720、60 Hz。先停止其他版本接收器，使用本版 .sdk/program_ethernet.bat 下载，再运行 host/start_station.ps1。进入工作台“网口传输”选择模式。默认仅预览、1 GiB 归档上限，限时测试才自动留图。

## 局限与下一步

这一版没有提高检测准确率，继承 V1.24 的四级算法、同材质改善与跨材质退化。旧 50 照片/230 正常图及 800 跨材质压力结果不是本版新盲测；真实相机、曝光、运动模糊仍未验收。五个原有 CDC 不安全端点、有限事件队列、未保存 DDR 掉电丢失、HDMI 前一帧红框等问题继续存在。

下一版优先探索编码与发送重叠，目标保留省流同时减少额外等待。必须先明确部分编码失败、断线、TCP 缓存引用与重发的所有权，逐步测试后再决定是否默认启用。后续再推进输入命令唯一身份、时钟/掉线同步及 CDC 审核，不能用 CRC 或传输指标替代算法盲测。
'''
(R/'docs/Tile_V1.25_无损位打包与实板报告.md').write_text(doc,encoding='utf-8')
print('V1.25 report generated from passed tests, including the measured latency tradeoff')
