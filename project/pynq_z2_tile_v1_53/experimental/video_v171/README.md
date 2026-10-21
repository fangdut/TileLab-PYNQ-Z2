# 连续视频 PL 调度与 HDMI 集成（待实板验收）

这部分是后续 HDMI 连续输入所需的硬件基础，不能作为已经完成视频检测的证据。V170 的自动重启微基准仅重复固定 DDR 图片，两者必须分开报告。

`pl_frame_scheduler.sv` 实现“采集提交 → AXI-Lite 启动检测核 → 等待核完成 → 允许下一帧采集”，不需要 ARM 逐帧启动。启动前 ARM 可以一次性装载模型、配置内存地址和尺寸；调度器拥有检测核期间 ARM 不得读取其 clear-on-read 完成标志或发出 start。AXI-Lite 的 AW/W 独立握手，遇到总线错误停止，无效采集帧不启动检测。

`roi_ddr_writer.sv` 接收像素时钟跨域后的 64 位令牌流，用最多 16 beat 的 AXI 突发写入固定输入缓冲区。AW/W 独立，保持反压时的数据和地址，最后一个写响应完成后才发布 commit。检查完整长度、帧号和 IEEE CRC32；错误帧仍排空但标记 invalid。超长包不会写出指定 ROI 范围，新 SOF 可在没有在途写事务时重新开始被中断的帧。

令牌协议：user=1 为 SOF，低 32 位是帧号；user=0 为两个按先后顺序装入低/高 32 位的 0x00RRGGBB 像素；user=2 为正常 EOF，数据为 `{crc32, frame_sequence}`；user=3 为无效 EOF。CRC 针对像素的内存小端字节序计算，SOF/EOF 不写入图像缓冲区。

独立 RTL 测试覆盖：独立地址/数据反压、命令稳定性、采集无效帧拒绝、总线错误停机、完整/部分突发、4 KB 边界、CRC 损坏、短包、超长包，以及禁止在 DDR 写响应完成前发布帧。CRC 黄金值由 Python zlib 从测试字节生成，未复制硬件 CRC 算法。

HDMI ROI 采集、异步 FIFO、丢帧/失锁恢复和模块连接已有 RTL 仿真覆盖；实际连续视频仍待实板验证。`capture_active` 是供采集模块同步的电平握手：一次采集完成后等待其归零，再接受下一次请求。所有权切换必须在 DDR 写完成后发生，不能以收到最后一个视频像素代替。


新增 `hdmi_detector_pipeline.v` 连接所有采集/写入/调度/结果锁存模块。`pl_result_latch.sv` 从 DDR 读取检测核最终结果头，在 PL 检查模型身份、任务数、尺寸、阈值判定和连续帧号，完整锁存后才释放下一次采集。`video_regs.v` 只提供一次性使能和观测接口，基址 0x43c20000；控制主机与 PL AXI 主机的检测核映射均显式固定为 0x43c10000。

寄存器：0x00 enable；0x04 status（bit0 所有权、1 采集、2 缺陷、3 结果有效、4 故障、5 HDMI 锁定）；0x08 已检测帧数；0x0c 拒绝帧数；0x10 原视频帧号；0x14 原视频 RGB CRC；0x18 故障码；0x1c 峰值；0x20 阈值；0x24 掩膜像素数；0x28 检测核帧号；0x2c 核内周期；0x30 版本 0x17100001；0x34 固定 ROI 尺寸。停机后须等待 status.bit0 归零，再由 PS/JTAG 访问图片缓冲区。运行时不能读取检测核的 clear-on-read 控制寄存器。

`video_alarm_border.v` 仅按整片图像判定显示红/绿边框，不表示像素裂纹位置。`tb_pipeline.sv` 在不同时钟和总线反压下连续处理三帧，检查 ROI 与通道顺序、无效帧拒绝、禁止覆盖检测输入、结果序号和自动停机。该测试里的 HLS 为总线模型，真实 CNN 数值另由 HLS C/RTL 与实板回归检验。该区别必须保留。

首个集成版本未通过时序，失败报告保留。HLS20 的后续 HDMI 集成实现已在 100 MHz 完成布局布线：setup 0.040 ns、hold 0.031 ns，DRC 错误 0，异步 FIFO bus skew 通过。该版本的 BIT/XSA/ARM 传输固件已生成，但下载时 JTAG 扫描不到板卡，尚未上板。不能把它当成完成 HDMI 实时验收的证据。

CDC 仅对经过拓扑检查的同步器第一级 D 和复位桥异步 PRE 引脚设置例外，未使用整组异步时钟 false path。复位请求的组合逻辑会触发一项 CDC-10 结构提示：实际为异步置位、四级同步释放的复位桥，需结合源码、约束与复位仿真审查，不能宣称 CDC 报告零 critical。

`source/RealPhotoSource.cs` 是独立 HDMI 输入播放器，仅显示校验过 SHA256 的原始真实照片，不执行检测。它只在唯一的 1280×720 外接屏上工作，把整张照片显示在中央 720×720 ROI；不把 WPF 刷新次数当成 HDMI 或检测帧率。源照片到屏幕可能经过重采样，HDMI 数值应以实际采集 DDR 内容为准。

使用 `source/build_source.ps1 -Out <新的 EXE 路径>` 编译播放器。`source/make_catalog.py --dataset <dataset_v168> --out <新的 catalog.json>` 默认选一张真实良品和一张真实裂纹照片；加 `--all-test` 则选择全部 117 张公开开发测试照片。清单生成器逐张检查原始文件 SHA256，不编辑照片。运行 `RealPhotoSource.exe <catalog.json> <status.json> 4 <command.txt>`；命令文件可写 `pause` 或 `close`。照片标签只属于输入资料，不参与 PL 判定。开发集的输入多样性不能替代独立准确率验收。

实板验收顺序：先下载新 BIT 和传输 ELF，完整重跑 117 张公开开发集照片；随后用 `scripts/texture_v170/video_control.py` 核对该次下载和回归的身份，停止两个 ARM 核，一次性使能 PL，观察实际采集帧号、CRC、完成数与故障码。脚本不逐帧发 start，不执行 CPU/GPU 检测。停机排空后 `video_snapshot.py` 可读取实际 HDMI 输入和 PL 掩膜，校验采集 CRC 以及结果头。以上脚本尚待本版本硬件验证。

`tools/fpga_texture_v170/audit_captured_reference.py --profile <冻结配置> --image <actual_hdmi_input.png> --result <raw_result.bin> --out <新目录>` 仅在实验后离线核对。它先从 Python 图与投影/码本配置重建 model.bin，要求与部署模型逐字节相同，再比较实际采集图像的评分、原尺寸掩膜和结果头；不使用原始 840×840 照片的期望分数代替 HDMI 采集图像。该工具通过了保存的 C++ 结果核对，并会拒绝人为翻转一个像素的掩膜；这两项属于离线工具测试，尚不构成 HDMI 上板证明。

每次构建将视频 RTL 和物理约束脚本复制到独立快照目录；通过时序、DRC 与 bus skew 后才导出可下载文件。软件构建继续要求外部 BIT 与 XSA 内 BIT 的完整 SHA256 相同，不能以忽略头部差异代替文件一致性检查。
