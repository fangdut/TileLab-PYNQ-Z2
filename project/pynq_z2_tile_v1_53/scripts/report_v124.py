from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_23'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={'firmware':'firmware_audit.json','hardware':'hardware_audit.json','simulation':'simulation_audit.json','mode_boundary':'mode_boundary/summary.json','invalid_modes':'invalid_modes_board.json','normal_board':'normal_board/summary.json','input_equality':'real_input_equality.json','transport_full':'transport_comparison.json','faults':'recovery/summary.json','restarts':'restart/summary.json','ui_restart':'ui_restart_after.json','admission_board':'admission_board/summary.json','stimulus_board':'stimulus_board/summary.json','station_full':'station_continuous.json','identity':'station_identity_audit.json','background':'background_summary.json','recovery_native':'dma_recovery_native.json','health_native':'health_native.json','mode_native':'mode_native.json'}
s={k:read(O/p) for k,p in files.items()};assert all(v['passed'] for v in s.values())
legacy=read(O/'real_board_legacy/summary.json');quad=read(O/'real_board/summary.json');assert legacy['passed'] and quad['passed']
cross=read(O/'cross_material/results.json');assert cross['completed'] and cross['images']==800
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 188 tests' in unit and unit.rstrip().endswith('OK')
summary=dict(version='V1.24',passed=True,unit_tests=188,**s,weak=dict(legacy=legacy,quad=quad),cross_material=cross,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),scope='Known-material weak-crack engineering improvement, not independent factory accuracy')
(O/'quad_weak_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
h=s['hardware'];fw=s['firmware'];n=s['normal_board'];b=s['background'];c=s['station_full'];a=s['identity'];plan=read(R/'ITERATION_PLAN.json')
transport='\n'.join(f"| {name} | {v['raw_request_ms']:.3f} | {v['compact_request_ms']:.3f} | {v['saving_percent']:.3f}% |" for name,v in s['transport_full']['summary'].items())
doc=f'''# Tile V1.24 四级弱裂纹检测与实板验收报告

## 本版做出了什么

在 PYNQ-Z2 上增加两级可选弱裂纹邻域支持，形成四级硬件流水；保留旧两级和纯高阈值模式。FPGA 继续以 74.25 MHz 接收 720p60，每像素检测、区域分析、产品跟踪与最佳截图选择仍在 PL 中执行。Vitis 仅增加新模式请求与产品间隙配置，DMA、队列、确认、恢复与传输的主体行为保持不变。电脑端能够选择配方，并按照截图实际携带的配置区分两级和四级结果。

这是一套指定材质的缺陷候选筛查与人工复核原型，尚不是任意瓷砖、任意相机条件下的工业成品。没有增加 YOLO 或把检测移到电脑。

## 实板改善及代价

新旧模式均在本次 V1.24 硬件上重新采集 50 张相同历史照片。50 对原图的 PNG 字节完全一致；每张掩码、区域框和区域面积均与独立参考逐像素比对。以下结果来自实际 HDMI→FPGA→DDR→以太网链路。

| 指标 | 旧两级，T=89 | 新四级，T=90 |
|---|---:|---:|
| 裂纹图触发报警 | {legacy['counts']['crack']['alarms']}/17 | {quad['counts']['crack']['alarms']}/17 |
| 正常图误报警 | {legacy['counts']['good']['alarms']}/33 | {quad['counts']['good']['alarms']}/33 |
| 裂纹像素召回率 | {legacy['pixel_recall']*100:.4f}% | {quad['pixel_recall']*100:.4f}% |
| 裂纹像素精确率 | {legacy['pixel_precision']*100:.4f}% | {quad['pixel_precision']*100:.4f}% |

召回率提升 {s['input_equality']['recall_increase_pp']:.4f} 个百分点，精确率变化 {s['input_equality']['precision_change_pp']:.4f} 个百分点。不是免费提升：额外生长会接纳少量非裂纹像素。图像级全数报警，也不意味着已经完整分割每一条裂纹；像素召回仍较低。

230 张历史正常训练照片也全部重新通过 HDMI 上板采集，{n['images']} 张像素与区域结果精确匹配，报警 {n['alarms']} 张。阈值在这次实板回归前已经冻结，没有根据本次测试图再选参数。历史素材已参与开发，所以这些数字不是独立盲测或工厂准确率。

## 原理与硬件资源

灰度 Y=(77R+150G+29B)>>8；四个方向、半径 8 的暗谷分数取 max(0,max_d(min(Y(p+8d),Y(p-8d))-Y(p)))。强候选大于 T，弱候选大于 ceil(T/2)。每级保持强/已接纳中心，或者当弱中心周围 3×3 至少有三个已接纳像素时晋升。执行两级或四级，不做无限递归。没有强种子的弱裂纹仍可能漏检。

增加流水级同时延迟原图、掩码和同步信号，吞吐率仍为每时钟一个像素。新增 3308 个像素时钟，约 44.552 微秒；这不等于提高电脑预览帧率。没有提高像素、AXI 或参考时钟频率。

| 资源 | 旧硬件 | V1.24 |
|---|---:|---:|
| LUT | 17049 | {h['resources']['Slice LUTs']:.0f} |
| 寄存器 | 28386 | {h['resources']['Slice Registers']:.0f} |
| BRAM Tile | 58 | {h['resources']['Block RAM Tile']:.0f} |
| DSP | 2 | {h['resources']['DSPs']:.0f} |

完整综合、布局、布线、BIT/XSA 导出成功。建立时间裕量 {h['wns_ns']:+.3f} ns，保持裕量 {h['whs_ns']:+.3f} ns；8 项总线偏斜约束通过。新 XSA 内嵌 BIT 与下载 BIT 完全一致。仍有 {h['cdc_unsafe_endpoints']} 个原有 CDC 不安全端点、部分 I/O 延迟及方法学警告，因此不能宣称所有可靠性问题都已消除。

## 配方、截图和产品同步

模式位 24 启用弱支持，位 25 启用额外两级。ARM 按产品间隙提交，FPGA 按帧边界应用。实板测试中，同一瓷砖仍在区域内时请求旧模式，连续读回仍保持原四级配置；离开之后才切换。已排队截图在新请求后读回，原图、掩码、帧号、配置和像素 CRC 保持一致。13 类非法模式/阈值请求被拒绝，队列和配置未改变。

旧 JTAG 调试通道不发送四级请求，界面会明确拒绝该组合；正式新模式通过以太网控制。截图归属基于采集配置，不按点击时的界面选项猜测。

## 传输与连续运动实测

50 对同一保留事件的 RAW/RLE 内容及描述逐字节一致，像素、响应头和原始描述的三类校验均通过。该版主要改善算法，未重写编码器；以下重新测量用于防止算法升级破坏传输。

| 输入 | RAW 请求中位数 ms | 压缩请求中位数 ms | 负载减少 |
|---|---:|---:|---:|
{transport}

连续移动 {c['seconds']:.3f} 秒，电脑接收 {c['host_captures']} 帧、保存 {c['saved']} 个缺陷产品；按输入条码复核，最大居中偏差 {a['max_center_error_px']} 像素，目标不超过 32 像素。没有专门在中央停车。冻结预览、继续后台收事件的模式，接收应用字节率减少 {b['received_rate_reduction_percent']:.3f}%；这些数字不包含 TCP/IP/链路头，也不代表电脑端每秒显示 60 帧。

## 逐步验证记录

188 项主机测试；772 项实际 C 配方边界；20 个实际 main.c DMA 恢复/帧槽场景；18 项健康边界与 25000 次随机操作；3000 组 CRC、1280 个描述单比特错误及 48 帧槽所有权测试通过。软件测试使用受控时间或 MMIO 桩，硬件结论来自独立实板记录。

RTL 检查包括 20736 像素两级/四级标记对齐、20736 像素中途复位后恢复、73728 个彩色像素整链路及 19840 像素旧模式/复位回归。模式、ROI、同步、亮度、候选数量和 CRC 都被检查。测试日志的 PASS 与错误内容共同决定结果，不能仅相信 Vivado 返回码。

本版另重测 4 组停止接收边界、9 类网络故障、3 类程序/板卡重启、UI 恢复待确认、3 组播放器文件冲突。异常数据不会作为正常证据确认。物理 DMA 停止和三次恢复预算的详细注入活动继承 V1.21 的实板证据，本版实际 C 回归通过；不将旧活动冒充本版新注入。

构建过程中一个 AXI 转换 IP 的 Vivado 进程发生内部访问违例。保留日志/转储，单独重跑失败 IP 后完成构建。另发现老测试参考仍按早期全局红框规则生成；同一失败在 V1.23 复现，按当前分区报警规则修正后新旧版本都通过。原反例和修正过程均保留。

## 不能隐去的跨材质退化

固定当前 HDMI 配方，800 张正常屋面陶瓷照片经 500 像素缩放居中后，旧两级/89 报警 547 张，新四级/90 报警 555 张；新增误报 14 张、消除 6 张。该测试没有用于再次调参。它与旧版使用源空间阈值 105 的压力统计不是同一个条件，不能混算。

结构边缘、纹理和不同尺度仍能触发暗谷规则。下一步需要分材质的正常校准和真正未参与开发的测试数据，再验证方向连续性、裂纹宽度和纹理抑制。真实相机、曝光、运动模糊、物理掉线和供电异常仍需另做测试。

## 保存、运行与后续

本工程位于 {R.as_posix()}，Vitis workspace 是同名 .sdk。旧 V1.23 原工程保留，轻量备份 {plan['backup']}，SHA256 {plan['backup_sha256']}。新 BIT SHA256 {h['artifacts_sha256']['system.bit']}；ELF SHA256 {fw['elf_sha256']}。使用 .sdk/program_ethernet.bat 下载配套 BIT/ELF，再用 host/start_station.ps1 打开工作台。连接方式保持电脑 HDMI→板 IN、板 OUT→显示器、USB PROG UART 与直连网线。

日常以预览模式运行，自动事件不会无限存盘；限时验收才开启归档，容量上限 1 GiB。正常训练复测保留少量代表图和全量统计/校验，失败时保留必要反例。

后续按小版本推进：先进一步减少难压缩画面和证据传输的字节量，同时保留完整原图与掩码的可验证重建；再加强输入命令身份、掉线后的同步及 CDC 审核。任何新方案先离线/边界测试，再实际传输与故障测试，通过后才作为默认行为。当前有限队列、未保存 DDR 断电丢失、上一帧 HDMI 红框、较高速度下居中不足，以及 PNG/SQLite 非跨文件事务等限制继续存在。
'''
(R/'docs/Tile_V1.24_四级弱裂纹与实板报告.md').write_text(doc,encoding='utf-8')
print('V1.24 full report and verified JSON generated')
