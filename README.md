# TileLab 项目入口

**当前匀速模拟流水线、完整工程与技术报告V208请进入 [fpga-real-texture-v170 分支](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170)。** 视觉计算核心沿用冻结V202；进入检测区截图经网口送往PL，未报警自动通过，报警到右侧后人工复核。

[报告PDF](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/project/pynq_z2_tile_v1_53/reports/v208/TileLab_比赛技术报告_V208.pdf) · [报告Word](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/project/pynq_z2_tile_v1_53/reports/v208/TileLab_比赛技术报告_V208.docx) · [工程重建与复现](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/docs/reproduction.md) · [指标与证据](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170/metrics)

报告已补入设备实拍和现场页面截图。输送由电脑模拟，HDMI用于电脑直连外屏显示；当前不包含板端HDMI取帧检测或物理分选。117图属于公开开发集。原创代码MIT，第三方数据和厂商代码保留原许可。参赛者原始视频尚未剪辑，比赛尚未提交。

以下V1.53.1为历史归档；其中算法、720p60及验收描述不代表当前V208流程。

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