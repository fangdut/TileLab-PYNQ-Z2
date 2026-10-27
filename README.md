# TileLab FPGA 实拍瓷砖检测

<!-- V200_CURRENT_BEGIN -->
**V200闭环功能版（2026-10-27）：** 已连接材质／冻结参照绑定、至少3张不同良品+1张已知缺陷工位核验、PL检测、人工复核接口、处置及CSV／JSON追溯。两套参照切换无需重下载BIT；旧结果、复核冲突和外部参照变更均不能良品放行。32项控制测试、实板22次API+2次浏览器回放通过；新交付包重新易失部署后再通过22次／38次拒绝。回放操作员明确标为自动化，不冒充真人复核。117张停驻节奏逐值回归通过（逐图间隔1秒），另一次无额外间隔39张后DDR复位中断仍保留，根因未定，不能宣称高负载长稳验收。100MHz PL和CNN未变，不在线学习任意花色。[功能、失败与验证记录](project/pynq_z2_tile_v1_53/reports/v200/status.html)。
<!-- V200_CURRENT_END -->

<!-- V199_CURRENT_BEGIN -->
**V199局部优化（2026-10-27）：** 检测模型及100MHz PL核心保持不变，ARM只优化传输CRC，PC只缩短直连网口的连接建立等待。相同32次原图测试均时0.54084→0.49865秒（约7.8%），117张完整结果逐值复核通过、均时0.50874秒，含一次建立连接重试；12次工位流程／34次拒绝操作通过，但该轮均时0.60786秒，长尾仍须披露。按材质参照的陶瓦40张新文件预留测试为20良品零误报／20缺陷检出；另32正常标定图仍有1误报，抬阈值候选漏检11/12已否决。不是彩绘地砖或实体工件独立验收。原稳定包保留，无新CNN训练、无新PL增频成果。[完整证据与失败记录](project/pynq_z2_tile_v1_53/reports/v199/status.html)。
<!-- V199_CURRENT_END -->

<!-- V198_CURRENT_BEGIN -->
**2026-10-27工程交付决定：94.6秒HFENet候选已否决，恢复100MHz整数MobileNetV2良品参照检测器。** 本轮117张公开实拍开发图上板逐值复核通过（33正常零误报、84缺陷检出），内核均时0.12473秒；传输加检测均时0.66486秒，包含4次连接建立重试。交付目录重新下载后12次流程和34次非合规操作拒绝通过。所有图像检测计算仍在PL；没有实体输送机构，开发集结果不是独立盲测准确率。工程和10页模板报告已形成，后续实拍、视频及提交由参赛者处理。[最终工程证据](project/pynq_z2_tile_v1_53/reports/delivery_20261027/status.html)。
<!-- V198_CURRENT_END -->

<!-- V197_CURRENT_BEGIN -->
**V197（2026-10-26）：** 复用作者HFENet预训练模型，无新训练；在作者80张原始扫描图上，浮点和整数参考均40/40缺陷检出、0/40良品误报，整数掩膜相差177/28835840像素。作者模型／作者数据复现，不是独立验收。预处理和动态归一化独立单元RTL通过，完整新网络尚未生成BIT或上板；原100MHz停驻工作站保留。[报告](project/pynq_z2_tile_v1_53/reports/v197/status.html)。
<!-- V197_CURRENT_END -->

<!-- V196_CURRENT_BEGIN -->
**V196（2026-10-26）：** FPGA前置固定ROI已在网口停驻模式通过8次坐标／背景工程核对；默认117张实板逐值一致。50 MHz时序通过，但HDMI试验无有效检测，候选不晋升，已恢复100 MHz稳定工作站。新地砖扫描图的线状分支离线只检出16/20，误报3/20，仍失败，尚未集成。不是新花色准确率验收。[完整结果](project/pynq_z2_tile_v1_53/reports/v196/status.html)。
<!-- V196_CURRENT_END -->


<!-- V195_CURRENT_BEGIN -->
**V195 良品参照标定（2026-10-25）：** 不改变FPGA内核，仅更新良品参照与阈值。第二轮新40张陶瓦实板39/40判对（良品误报1/20、缺陷检出20/20），另40张已公开回归全部判对；80张评分/掩膜逐值一致。不是彩绘地砖或实体独立验收，候选不进入自动放行。[完整结果](project/pynq_z2_tile_v1_53/reports/v195/status.html) · [离线标定与部署](project/pynq_z2_tile_v1_53/tools/fpga_texture_v170/REFERENCE_CALIBRATION.md)。
<!-- V195_CURRENT_END -->

<!-- V194_CURRENT_BEGIN -->
**V194 外部验证与范围联锁（2026-10-25）：** 新来源40张陶瓦原图的冻结配置压力测试失败：20张缺陷检出，但20张良品全部误报；不能当作地砖或任意材质验收。原117张纹理图仍逐值一致。工作站新增未验证输入只显示参考结果、禁止良品放行；13项软件测试与4项实际FPGA界面检查通过。这是流程资格约束，不是检测准确率提升。[完整结果](project/pynq_z2_tile_v1_53/reports/v194/status.html) · [技术报告底稿](project/pynq_z2_tile_v1_53/reports/v194/technical_report_draft.html)。
[V194本地运行包清单与校验值](deliverables/TileLab_StopInspect_V194_Dev.json)（含未验证输入复核流程；原40张误报结果完整保留）。
<!-- V194_CURRENT_END -->

<!-- V193_CURRENT_BEGIN -->
**V193 停驻检测工作站（2026-10-25）：** 已完成“固定输入→FPGA检测→确认良品放行／缺陷隔离”的可操作原型。12张实拍开发样例全流程通过，34次不合规操作被拒绝；平均PL约125 ms、传输与检测约0.54秒。10项软件联锁测试及3项真实FPGA界面检查通过。PC管理流程，检测全部在PL；无实体传送带，当前处置为逻辑指令。10 FPS暂不作为交付前提，下一步独立真图验证和提交材料。[工作站说明](project/pynq_z2_tile_v1_53/host/stop_inspect_station/README.md) · [验收记录](project/pynq_z2_tile_v1_53/reports/v193/status.html)。
[本地开发包清单与校验值](deliverables/TileLab_StopInspect_V193_Dev_R1.json) · [从仓库生成运行包](project/pynq_z2_tile_v1_53/tools/package_stop_station.py)（319项文件完整性与部署检查通过；已使用包内程序重新上板并复测）。
<!-- V193_CURRENT_END -->

<!-- V192_CURRENT_BEGIN -->
**V192 上板复测（2026-10-24）：** 本轮100 MHz完整117图HDMI复测通过：8.1714 FPS，243.778秒内完成1992次检测；119次双ARM停止检查，CPU逐帧启动为0。 125 MHz仍未稳定通过；10 FPS目标尚未验收。修复视频JTAG连接的1 MHz显式设置及CAD超时子进程清理，保留失败和对照记录。[报告](project/pynq_z2_tile_v1_53/reports/v192/status.html)。
<!-- V192_CURRENT_END -->

<!-- V190_CURRENT_BEGIN -->
**V190 硬件实验（2026-10-24）：** HLS79把采用精确24位累加和第四路DSP量化，117张开发集C输出及完整AXI RTL两次启动13302个字一致。本体实际资源见报告；整机阶段 `FAILED_NO_PROMOTION`（100 MHz / ExploreArea），尚无新版板端FPS。HLS76整机布局超容失败已留档。历史验收基线仍为V179约8.17 FPS。[实验记录](project/pynq_z2_tile_v1_53/reports/v190/status.html)。
<!-- V190_CURRENT_END -->

<!-- V188_CURRENT_BEGIN -->
**V188 硬件实验（2026-10-24）：** 32路卷积已接入完整检测器，117张开发集C评分/掩膜逐值一致；完整AXI RTL两次启动共13302个字一致。检测器本体实际综合48726 LUT、217 DSP、118 BRAM Tile，完整HDMI系统阶段为 `FAILED_NO_PROMOTION`。尚无新版板端帧率，持续基线仍为V179约8.17 FPS。[实验记录](project/pynq_z2_tile_v1_53/reports/v188/status.html)。
<!-- V188_CURRENT_END -->

目标是让图像预处理、特征提取和缺陷判定全部运行在 PYNQ-Z2 的 PL 中，电脑与 ARM 仅负责输入、传输、控制和显示。

**当前板端状态（2026-10-23）：** 当前板端已恢复 100 MHz V179：连续 HDMI 8.168911 FPS，1996 次 / 244.341 秒，117/117 判对、0/33 误报、17/17 裂纹检出；测量期间双 ARM 核暂停检查 119 次。测试结束后已恢复 ARM0 的传输服务。V186 此前在重新连接的 USB 接口上启动，完成 117 张真实图片的全部分数及原尺寸掩膜逐值核对，117/117 判对、0/33 正常图误报、17/17 裂纹检出；固定图片自动运行 10.524375 FPS。连续 HDMI 在完成 35 张图片后中断，随后读到 DDR 控制器复位；本次连续视频验收未通过，没有完整连续 FPS 结果。 这是反复使用的公开开发集，非独立盲测。[本轮状态](project/pynq_z2_tile_v1_53/reports/v186/status.html)。

| 阶段 | 已有证据 | 尚未完成 |
|---|---|---|
| V169 完整浮点 PL 基线 | 两张真实良品/裂纹照片已上板，评分和掩膜与参考一致；单张约 553 秒 | 无实时能力，非完整准确率验收 |
| V170 已验证快照（HLS11） | 117 张真实照片已全部上板判对，评分/掩膜逐点一致；硬件自动运行 2.695 FPS | 尚未达到 10 FPS 或连续 HDMI 验收 |
| V170 已验证快照（HLS15） | 同一批 117 张全部上板逐值一致；硬件自动运行 **4.279 FPS** | 尚未达到 10 FPS 或连续 HDMI 验收 |
| V171 缓存版（HLS23/HW04） | 117 张全部上板，评分和掩膜逐值一致；固定帧 PL 自动运行 **6.299 FPS**；100 MHz 时序和 FIFO 双向 bus skew 通过 | 尚未达到 10 FPS；117 张属于反复使用的开发集 |
| V171 未校正 HDMI 基线 | 两个 ARM 核暂停时持续检测；117 张中 84/84 缺陷检出 | **33/33 良品误报**，该失败基线完整保留 |
| V172 FPGA 颜色校正 + HDMI | **117/117 判对，0/33 良品误报，84/84 缺陷、17/17 裂纹检出**；连续 254.101 秒自主完成 1386 次检测，**5.455 FPS**；ARM 双核暂停检查 119 次 | 属于公开开发集；尚未完成独立盲测、细裂纹定位与持续 10 FPS 验收 |
| V173 双路并行实验（HLS30–32） | HLS30 完整 RTL 通过；HLS30–32 各自的 117 张离线评分/掩膜逐值一致 | HLS30 共享与分流 DDR 工程均被布局拒绝；31/32 尚未完成 RTL/整机验证，没有新系统帧率 |
| V173 已验证掩膜流水线（HLS34） | **117/117 原始照片和 HDMI 均通过，正常图 0/33 误报、裂纹 17/17 检出**；连续 250.424 秒自主完成 1503 次检测，**6.002 FPS**；固定帧 **6.570 FPS**；100 MHz 时序 +0.133 ns | 同一公开开发集；尚未完成独立盲测、细裂纹定位与持续 10 FPS 验收 |
| V173 两行复用实验（HLS35） | 117 张离线评分/掩膜逐值一致；真实裂纹与奇数行专项 C 检查通过 | 尚无 RTL/板端验收 |
| V173 多行批次（HLS38） | 117 张 C 评分/掩膜一致，两次缩小配置 RTL 检测通过 | 完整 HDMI 硬件由后续 HLS39 合并验证，尚未单独上板 |
| **V173 R2 已验证（HLS39）** | **117/117 原始照片和 HDMI 均通过，0/33 良品误报、17/17 裂纹检出**；连续 248.879 秒自主完成 1659 次检测，**6.666 FPS**；固定帧 **7.539 FPS**；ARM 双核暂停检查 119 次 | 公开开发集；尚未完成独立盲测、细裂纹定位与持续 10 FPS 验收 |
| V174 直接缓存实验（HLS50/51） | 117张C与实板全输出精确一致，100MHz修复后时序通过 | 实板固定帧7.444 FPS，低于原版7.539；不晋升，已恢复HLS39；无本轮HDMI结果 |
| V175 采集/推理重叠（沿用 HLS39） | 四槽调度、独立控制、动态 DDR 写入、结果身份、寄存器及 HPD 共六组 RTL 检查通过 | HW02 初始时序 −0.482 ns，修复后仍 −0.279 ns；未下载，未测板端吞吐 |
| V176 关键路径与频率实验（HLS52/53） | 217 种合法尺寸穷举通过；117 张完整 C 输出文件与 HLS39 字节一致；两次缩小配置 RTL 通过，IP 已导出；125 MHz 时钟接口连接检查通过 | HW03 在 125 MHz 下时序 −1.571 ns，修复后仍 −1.352 ns；未下载，无新实板速度 |

| V178 坐标查表（HLS55/56） | 117 张完整 C 输出与 HLS39 字节一致；两次缩小配置 RTL 通过，IP 已导出 | 125 MHz 实际时序 −0.653 ns；未通过，未下载 |
| **V179 已验证（HLS62）** | **117/117 原始照片及 HDMI 均通过；0/33 良品误报、17/17 裂纹；连续 239.548 秒完成 1,957 次自主检测，8.170 FPS；固定帧 8.021 FPS；ARM 双核暂停检查 119 次；100 MHz 时序通过** | 同一公开开发集；持续 10 FPS、独立盲测及精细定位仍待完成 |
| V180 DDR 分流＋125 MHz | 沿用完全相同的 HLS62 检测内核；共享/分流实际端口与时钟检查通过 | 125 MHz 实际建立时间 −0.598 ns，未通过、未下载；Winograd 仅完成独立数学检查，尚未接入检测器 |

| V182 指令控制译码（HLS64/65） | 117 张完整 C 输出与已验收版字节一致；100,268 个操作码检查及四种非法模型错误路径一致；生成 RTL 已确认两级译码寄存 | 两次完整功能缩小配置 RTL 通过（545,278 / 545,286 周期），IP 已导出；125 MHz 建立时间初始 −0.490 ns、一次修复后 −0.187 ns，未通过、未下载 |

| V183 结果校验流水线 | 与已验收历史 RTL 对照 6,190 次事务，覆盖错误头、DDR 错误、序号回绕及复位；采集/推理集成仿真通过，七组源文件绑定 | 沿用 HLS65，125 MHz 初始建立时间 −0.342 ns，一次物理修复后仍为 −0.015 ns，未通过、未下载；暂无新实板吞吐 |

| V184 行地址位宽实验（HLS66） | 117 张完整输出字节一致；2,578 万几何检查、104 万实际辅助函数输入及生成 RTL 单元检查通过；HLS 估计少 1 个 DSP | 尚无完整检测器 RTL、整机时序或上板结果；单独的 HLS67 完整 RTL 队列已取消，改为 V185 合并行地址与插值流水线修复 |

| V185 特征插值流水线 | 针对 V183 实际 11 级组合路径，将横向、纵向插值拆为各两拍独立模块；保留 V184 行地址修复与原舍入公式 | 117 张完整输出字节一致；39 万次生成 RTL 单元检查、结构检查与 HLS68 综合通过；HLS69 两次完整功能缩小配置 RTL 通过（547,158 / 547,166 周期），IP 已导出；125 MHz 实际建立时间 −0.786 ns，未通过、未下载 |

| V186 预处理/卷积缓存分离 | 独立 224×24 位 RGB 暂存，卷积行缓存保持 2048×128 位；完整 C117 和两次缩小配置 RTL 通过；125 MHz 整机时序 +0.003 ns / +0.025 ns，DRC 0，218 DSP / 128 BRAM | acceptance04 已完成 117 张全部分数与掩膜逐值核对，固定图片 10.524375 FPS；连续 HDMI 在完成 35 张图片后中断，随后读到 DDR 控制器复位；本次连续视频验收未通过，没有完整连续 FPS 结果。 |

117 张为反复使用的 MVTec Tile 开发基准，已用于方案比较，不能作为独立盲测或任意彩绘/多材质准确率。当前不宣称已经达到实时检测或比赛最终验收。最新已验证编译文件、实拍示例与实验记录见 [V179 开发快照](deliverables/V179_Verified_HDMI_8p17FPS_Dev.zip)；[V179 实板报告](project/pynq_z2_tile_v1_53/reports/v179/report.html)；[V173 R2 开发快照](deliverables/V173R2_Verified_HDMI_6p67FPS_Dev.zip)；[V173 掩膜快照](deliverables/V173_Verified_HDMI_6p00FPS_Dev.zip)；[V172 快照](deliverables/V172_Verified_HDMI_5p45FPS_Dev.zip) 与 [旧 V170 完整快照](deliverables/V170_Verified_FullPL_4p28FPS_R1.zip) 保留。首个速度目标是持续 10 次检测/秒，需分别报告核内速度、文件传输速度和连续视频速度。

- [工程状态与职责划分](FPGA_MIGRATION_STATUS.md)
- [V169 源码、构建、部署说明](project/pynq_z2_tile_v1_53/experimental/texture_v169/README.md)
- [V169 实板验收证据](project/pynq_z2_tile_v1_53/reports/v169/acceptance.json)
- [V169 两张照片的实板原始记录](project/pynq_z2_tile_v1_53/reports/v169/board_evidence.zip)
- [V169 匹配 BIT/XSA/ELF/HLS 编译包](project/pynq_z2_tile_v1_53/reports/v169/V169_FPGA_Migration_Verified_compiled.zip)
- [V170 冻结整数模型与说明](project/pynq_z2_tile_v1_53/models/texture_v170_r1/README.md)
- [V170 全部 117 张 C++ 算术回归](project/pynq_z2_tile_v1_53/reports/v170/full_c_summary.json)
- [HDMI 候选的时序与文件身份](project/pynq_z2_tile_v1_53/reports/v171/hls20_timing_closed/candidate.json)
- [HLS23 完整照片回归](project/pynq_z2_tile_v1_53/reports/v170/experiments/hls23_full_c_summary.json)
- [HLS23 实板 117 张结果](project/pynq_z2_tile_v1_53/reports/v171/hls23_verified/board_summary.json)
- [HLS23 实际 HDMI 吞吐](project/pynq_z2_tile_v1_53/reports/v171/hls23_hdmi_throughput/report.json)
- [V172 颜色模块验证](project/pynq_z2_tile_v1_53/reports/v172/color_rtl/summary.json)
- [未校正 HDMI 的 117 张失败基线](project/pynq_z2_tile_v1_53/reports/v172/uncorrected_hdmi117/summary.json)
- [V172 真实 HDMI 开发验收与文件身份](project/pynq_z2_tile_v1_53/reports/v172/verified_hdmi/verification.json)
- [V172 校正后全部 117 张结果](project/pynq_z2_tile_v1_53/reports/v172/verified_hdmi/hdmi117/results.json)
- [V173 单 DSP 提速原型](project/pynq_z2_tile_v1_53/experimental/packed_mac_v173/README.md)
- [视频 PL 架构与实板验收步骤](project/pynq_z2_tile_v1_53/experimental/video_v171/README.md)
- [历史 V167 完整工程](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/single-tile-reference-v167)

V169 的约 100 MB 模型可由冻结压缩配置与官方预训练权重精确重建，见源码说明；本地完整运行包包含该模型。V170 model.bin 已随源码保存。Python/Torch 算法脚本仅用于离线开发、标定和核对，板端运行不使用电脑 CPU/GPU 推理后备。

原创代码采用 [MIT](LICENSE)。MVTec 实拍照片、数据派生的模型/配置和相关证据保留 CC BY-NC-SA 4.0，AMD/Xilinx IP 与上游预训练权重保留原许可；详见 [LICENSE_SCOPE.md](LICENSE_SCOPE.md)。

此前已验证 V173 的源文件／下载身份、250 秒连续 HDMI 记录与逐图结果见 [实板证据](project/pynq_z2_tile_v1_53/reports/v173/verified_hdmi_hls34/verification.json)。它保持原模型和阈值，连续 HDMI 速度比 V172 提高约 10.03%。

此前 V173 R2 的 [实板证据](project/pynq_z2_tile_v1_53/reports/v173/verified_hdmi_hls39_r2/verification.json) 记录了全部 117 张结果、248.879 秒连续运行与 300 次通信查询。R2 保持模型和阈值，HDMI 速度比最初 V172 提高约 22.21%。曾有一次 TCP 建连超时和一次源状态文件权限错误；失败记录完整保留，后续两轮原始照片回归和本轮 HDMI 复测均通过。源状态读取现有有界重试及失败停机处理，TCP 超时原因未完全确定。

V179 的 [实板证据](project/pynq_z2_tile_v1_53/reports/v179/verified_hdmi_overlap/verification.json) 绑定了原模型、匹配 BIT/XSA/ELF、全部 117 张结果和连续 HDMI 计数。连续吞吐比 V173 R2 提高约 22.56%，固定帧提高约 6.40%；整机 42,482 LUT、218 DSP、127.5 BRAM。源码冻结为 HLS62，Winograd 尚未集成。

V187 的独立精确双路 DSP 算术实验已通过全部 16,777,216 个 signed8 三元组穷举、614,312 次 RTL 输出检查及独立 1 DSP 综合。它尚未接入检测器，不代表整机资源减半或帧率翻倍。见 [实验说明](project/pynq_z2_tile_v1_53/experimental/packed_pe_v187/README.md)。
