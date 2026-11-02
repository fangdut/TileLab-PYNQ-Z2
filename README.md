# 多算子低延迟工业视觉检测系统

基于FPGA的瓷砖表面缺陷筛查系统，工程代号TileLab。

**当前竞赛提交整理版V209：工程包、技能包、设计报告三合一。** 对照AMD自主选题初级组指南3.3.5整理；运行软件保持V208、PL核心保持冻结V202。本次主要修订目录、文件命名、缺失构建依赖、技能复用证据和报告。

- [三合一提交目录与复现](submission/v209/README.md)
- [设计报告Word](submission/v209/report/design_report.docx) · [PDF](submission/v209/report/design_report.pdf)
- [技能包与复用验证](submission/v209/skill/README.md)
- [大模型协作及自我纠错记录](submission/v209/report/llm_collaboration.md)
- [指南逐项审查](submission/v209/report/requirements_review.md)
- [中英文海报](submission/v209/report/poster.pptx)

submission/v209为最新提交根目录，路径使用英文ASCII普通小写，保留指南README.md惯例。build/file_map.json将规范化源文件恢复到指定的包外运行目录，逐文件保持原工程字节、大小写和部署清单。723文件恢复、原660项部署清单及配对检查通过，11项通用技能复用检查通过。报告15页。

电脑模拟真实照片匀速输送，进入检测区即截图经网口交给PYNQ-Z2 PL；有效未报警结果自动通过，报警或结果迟到在复核区停止。视觉算术在PL，电脑负责动画、截图、显示与复核，PS负责网络和控制。外屏由电脑HDMI直连，未使用板端HDMI取帧检测。

117图是反复参与开发的公开数据，不代表独立准确率。历史同32图传输优化约7.80%，不与PL微基准或完整应用耗时混用。当前无实体输送/剔除；本轮未重新综合、重新上板或跨板验证PYNQ Overlay/DMA。通用Python校验技能不冒充PYNQ框架插件。

原创代码MIT，数据、派生参照与厂商内容保留原许可，见提交目录许可说明。签名授权书、账号口令和个人视频不公开。历史V208及更早材料仍保留，入口以本页最新目录为准。
