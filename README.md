# TileLab 项目入口

**当前停驻检测原型请进入 [fpga-real-texture-v170 分支](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170)。** 工程冻结V202，当前技术报告V205；[报告](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/project/pynq_z2_tile_v1_53/reports/v205/TileLab_比赛技术报告_V205.docx)、[复现步骤](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/docs/reproduction.md)与[指标及证据](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170/metrics)见该分支。

以下V1.53.1为历史归档，其中算法、720p60与验收描述属于旧版本，不代表V202当前系统。当前为公开实拍照片回放的单片停驻原型，117图为开发集；视觉计算在PL，复核/处置为逻辑流程。

---

# TileLab 最终提交修订 V1.53.1

公开仓库：[TileLab-PYNQ-Z2](https://github.com/fangdut/TileLab-PYNQ-Z2)。

[完整工程与使用说明](project/pynq_z2_tile_v1_53/README.md)

- [比赛模板技术报告](submission_documents/TileLab_比赛技术报告_模板版.docx)
- [技术与教学手册](project/pynq_z2_tile_v1_53/docs/TileLab_最终提交版_技术与教学手册.pdf)
- [演示视频详细拍摄方案](project/pynq_z2_tile_v1_53/docs/TileLab_演示视频详细拍摄方案.pdf)
- [V1.53 实板核心验收](project/pynq_z2_tile_v1_53/reports/v153/final_validation_summary.json)
- [修订增量验收](project/pynq_z2_tile_v1_53/reports/v1531/summary.json)
- [第三方来源与许可](project/pynq_z2_tile_v1_53/THIRD_PARTY_NOTICES.md)

FPGA 承担 720p60 检测、标框和产品最佳帧选择，ARM 承担以太网传输与控制，电脑承担证据持久化和人工复核。已做真实板卡测试，尚未验证工厂相机；独立大理石漏检明显，详情见手册。保留工程文件夹名，`.sdk` 文件夹是 Vitis workspace。
