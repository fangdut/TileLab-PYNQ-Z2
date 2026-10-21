# TileLab FPGA 实拍瓷砖检测

目标是让图像预处理、特征提取和缺陷判定全部运行在 PYNQ-Z2 的 PL 中，电脑与 ARM 仅负责输入、传输、控制和显示。

| 阶段 | 已有证据 | 尚未完成 |
|---|---|---|
| V169 完整浮点 PL 基线 | 两张真实良品/裂纹照片已上板，评分和掩膜与参考一致；单张约 553 秒 | 无实时能力，非完整准确率验收 |
| V170 已验证快照（HLS11） | 117 张真实照片已全部上板判对，评分/掩膜逐点一致；硬件自动运行 2.695 FPS | 尚未达到 10 FPS 或连续 HDMI 验收 |
| V170 已验证快照（HLS15） | 同一批 117 张全部上板逐值一致；硬件自动运行 **4.279 FPS** | 尚未达到 10 FPS 或连续 HDMI 验收 |
| V171 缓存版（HLS23/HW04） | 117 张全部上板，评分和掩膜逐值一致；固定帧 PL 自动运行 **6.299 FPS**；100 MHz 时序和 FIFO 双向 bus skew 通过 | 尚未达到 10 FPS；117 张属于反复使用的开发集 |
| V171 未校正 HDMI 基线 | 两个 ARM 核暂停时持续检测；117 张中 84/84 缺陷检出 | **33/33 良品误报**，该失败基线完整保留 |
| V172 FPGA 颜色校正 + HDMI | **117/117 判对，0/33 良品误报，84/84 缺陷、17/17 裂纹检出**；连续 254.101 秒自主完成 1386 次检测，**5.455 FPS**；ARM 双核暂停检查 119 次 | 属于公开开发集；尚未完成独立盲测、细裂纹定位与持续 10 FPS 验收 |
| V173 提速算术原型 | 单 DSP 两路 INT8 乘法；全 16,777,216 组数学核对通过，RTL 与 HLS 协同仿真通过 | 尚未集成完整 CNN，没有新系统帧率 |

117 张为反复使用的 MVTec Tile 开发基准，已用于方案比较，不能作为独立盲测或任意彩绘/多材质准确率。当前不宣称已经达到实时检测或比赛最终验收。已验证编译文件、实拍示例与实验记录见 [V172 开发快照](deliverables/V172_Verified_HDMI_5p45FPS_Dev.zip)；[旧 V170 完整快照](deliverables/V170_Verified_FullPL_4p28FPS_R1.zip) 保留。首个速度目标是持续 10 次检测/秒，需分别报告核内速度、文件传输速度和连续视频速度。

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
