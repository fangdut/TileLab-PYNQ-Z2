# 多算子低延迟工业视觉检测系统

基于FPGA的瓷砖表面缺陷筛查系统，工程代号TileLab。

**最新三合一提交整理版V209请进入 [submission/v209](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170/submission/v209)。** 包含完整工程文件、技能包和15页设计报告及协作记录，按AMD自主选题初级组3.3.5整理。

[提交说明](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/submission/v209/README.md) · [报告PDF](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/submission/v209/report/design_report.pdf) · [技能包](https://github.com/fangdut/TileLab-PYNQ-Z2/tree/fpga-real-texture-v170/submission/v209/skill) · [逐项审查](https://github.com/fangdut/TileLab-PYNQ-Z2/blob/fpga-real-texture-v170/submission/v209/report/requirements_review.md)

运行应用保持V208、PL保持冻结V202。电脑模拟匀速真实照片输送，经网口送PL检测，正常自动通过、异常停驻复核。11项通用技能检查通过，本轮未重新综合或跨板验证PYNQ Overlay/DMA。117图是公开开发集。原创代码MIT，数据与厂商内容保留原许可。

以下为旧版历史归档，不代表V209的目录与指标。

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