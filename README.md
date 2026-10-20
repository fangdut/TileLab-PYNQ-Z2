# TileLab FPGA 实拍瓷砖检测

目标是让图像预处理、特征提取和缺陷判定全部运行在 PYNQ-Z2 的 PL 中，电脑与 ARM 仅负责输入、传输、控制和显示。

| 阶段 | 已有证据 | 尚未完成 |
|---|---|---|
| V169 完整浮点 PL 基线 | 两张真实良品/裂纹照片已上板，评分和掩膜与参考一致；单张约 553 秒 | 无实时能力，非完整准确率验收 |
| V170 全整数实时候选 | CNN 计算量约降至 1/175，模型 751,760 字节；历史 117 张真实照片全部判对，完整 HLS C++ 的评分和掩膜逐点一致 | 实际资源/时序收敛、上板帧率、持续 HDMI 输入验证 |

117 张为反复使用的 MVTec Tile 开发基准，已用于方案比较，不能作为独立盲测或任意彩绘/多材质准确率。当前不宣称已经达到实时检测或比赛最终验收。首个速度目标是持续 10 次检测/秒，需分别报告核内速度、文件传输速度和连续视频速度。

- [工程状态与职责划分](FPGA_MIGRATION_STATUS.md)
- [V169 源码、构建、部署说明](project/pynq_z2_tile_v1_53/experimental/texture_v169/README.md)
- [V169 实板验收证据](project/pynq_z2_tile_v1_53/reports/v169/acceptance.json)
- [V169 两张照片的实板原始记录](project/pynq_z2_tile_v1_53/reports/v169/board_evidence.zip)
- [V169 匹配 BIT/XSA/ELF/HLS 编译包](project/pynq_z2_tile_v1_53/reports/v169/V169_FPGA_Migration_Verified_compiled.zip)
- [V170 冻结整数模型与说明](project/pynq_z2_tile_v1_53/models/texture_v170_r1/README.md)
- [V170 全部 117 张 C++ 算术回归](project/pynq_z2_tile_v1_53/reports/v170/full_c_summary.json)
- [历史 V167 完整工程](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/single-tile-reference-v167)

V169 的约 100 MB 模型可由冻结压缩配置与官方预训练权重精确重建，见源码说明；本地完整运行包包含该模型。V170 model.bin 已随源码保存。Python/Torch 算法脚本仅用于离线开发、标定和核对，板端运行不使用电脑 CPU/GPU 推理后备。

原创代码采用 [MIT](LICENSE)。MVTec 实拍照片、数据派生的模型/配置和相关证据保留 CC BY-NC-SA 4.0，AMD/Xilinx IP 与上游预训练权重保留原许可；详见 [LICENSE_SCOPE.md](LICENSE_SCOPE.md)。
