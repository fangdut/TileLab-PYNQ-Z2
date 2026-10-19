# TileLab 单片瓷砖：V164工程与V165参照原型

使用者已确认按花色做良品参照标定。最新研究在 `single-tile-reference-v165` 分支：[参照原型运行说明](project/pynq_z2_tile_v1_53/README_REFERENCE_V165.md)、[图文结果](project/pynq_z2_tile_v1_53/reports/v165/reference_report.html)。已新增离线参照算法与独立整数差分RTL；**尚未接入完整板端，当前下载产物仍为V164**。没有新分类模型训练，没有真实彩绘裂纹准确率验收。

`single-tile-v164` 分支保留此前工程快照；以下V164验证与其报告属于该阶段的历史证据。当前研究状态以 `reports/v165/STATUS.json` 为准。

目标：先完成单片检测，再考虑多砖墙面与新模型训练。目标材料包含彩绘与多种材质。

**当前为可复现的工程候选，彩绘／多材质高准确率尚未达标，不是已验收的比赛最终版。** 保留失败样本与两种输入链路的差异，不以历史纹理结果替代目标材料验证。

- [项目说明与运行方法](project/pynq_z2_tile_v1_53/README.md)
- [当前验证状态](project/pynq_z2_tile_v1_53/reports/v164/QUALIFICATION.json)
- [回归图片与失败案例](project/pynq_z2_tile_v1_53/reports/v164/validation.html)
- [当前部署包](project/pynq_z2_tile_v1_53/releases/v164/DEPLOYMENT.json)：仅在匹配 BIT、XSA、ELF 完成编译并通过时序后生成。

本次沿用已经冻结的 V159 整数树检测器，没有进行新模型训练。在线检测在 FPGA PL；ARM 与电脑工作站负责传输、复核和留证。离线 Python 参考程序独立存放，不能当作上板测试。

V1.53 原工程、历史报告和提交文档保留用于追溯；其板测通过结论、旧 BIT/ELF 与原始 `PACKAGE_MANIFEST.json` 不代表本次 V1.64 的验收。当前入口为 `host/start_single_tile.ps1` 和 `scripts/program_single_tile.py`，不会自动下载历史固件。

数据来源和许可见项目 [数据说明](project/pynq_z2_tile_v1_53/DATA_PROVENANCE_V164.md)。未上传许可未澄清的 HFENet 图片包。
