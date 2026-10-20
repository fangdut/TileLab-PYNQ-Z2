# TileLab 单片瓷砖：V1.67.2完整参照检测工程

当前分支 `single-tile-reference-v167` 已集成完整HDMI采集、DDR全图FPGA差分、按花色标定与网页工作站。[运行与重新构建](project/pynq_z2_tile_v1_53/README_REFERENCE_V167.md)、[设计报告](project/pynq_z2_tile_v1_53/reports/v167/design_report.pdf)、[实际开发板演示剪辑](project/pynq_z2_tile_v1_53/reports/v167/demo_replay.mp4)、[当前验收状态](project/pynq_z2_tile_v1_53/reports/v167/STATUS.json)。24张实际HDMI回放通过，12幅差异图共300万像素与独立参考一致，五种协议故障均恢复。所有图片均为明确标识的程序生成测试图。

[完整提交候选包（约63 MB）](deliverables/tilelab_reference_v167_r2.zip)包含374个文件：源工程、匹配BIT/XSA/ELF、构建与下载脚本、独立演示图源、报告、视频、失败样本及实板原始记录。[包哈希与解压验证](deliverables/package_info.json)。工程内容已经打包；正式参赛前仍需核对当届模板及补充实体准确率证据。

归档的2026 AMD选题指南3.3.3.3要求明确的可再分发开源许可；当前尚无作者授权选择，[MIT草案](project/pynq_z2_tile_v1_53/reports/v167/license_proposal.txt)仅供审阅，未生效。第三方Digilent/AMD/Xilinx代码保留原有许可。[许可状态](project/pynq_z2_tile_v1_53/reports/v167/LICENSE_STATUS.json)。

最新108个程序用例：60张正常图无报警、无拒判；36张人工细线检出33张，保留3张弱单像素漏检；12张超限位姿均拒判。**工程链路通过，独立实体瓷砖准确率尚未验收**。电脑负责配准和连通区域，PL负责完整图像定点差分；输入720p60，完整检测约0.98秒。完整交付包及校验结果见下方提交材料。以下内容为历史阶段说明。

最新研究在 `single-tile-reference-v166` 分支：[V166运行与验收说明](project/pynq_z2_tile_v1_53/README_REFERENCE_V166.md)、[图文结果与实板证据](project/pynq_z2_tile_v1_53/reports/v166/reference_report.html)。按花色良品参照、固定视野与光照推进，改进了JPEG误报并保留弱线失败。实际板测包括V164检测器的50张HDMI回放和独立新窗口算术自检；**完整V166参照视频算法尚未集成，彩绘／多材质独立准确率尚未验收**。没有新分类模型训练。

`single-tile-v164`、`single-tile-reference-v165` 分支保留此前快照；以下V164验证与其报告属于该阶段的历史证据。当前研究状态以 `reports/v166/STATUS.json` 为准。原V164部署包保持原字节；脱离外接显示器依赖的HDMI通路另存在 `releases/v166_headless_transport`，不是V166参照检测算法。

目标：先完成单片检测，再考虑多砖墙面与新模型训练。目标材料包含彩绘与多种材质。

**当前为可复现的工程候选，彩绘／多材质高准确率尚未达标，不是已验收的比赛最终版。** 保留失败样本与两种输入链路的差异，不以历史纹理结果替代目标材料验证。

- [项目说明与运行方法](project/pynq_z2_tile_v1_53/README.md)
- [当前验证状态](project/pynq_z2_tile_v1_53/reports/v164/QUALIFICATION.json)
- [回归图片与失败案例](project/pynq_z2_tile_v1_53/reports/v164/validation.html)
- [当前部署包](project/pynq_z2_tile_v1_53/releases/v164/DEPLOYMENT.json)：仅在匹配 BIT、XSA、ELF 完成编译并通过时序后生成。

本次沿用已经冻结的 V159 整数树检测器，没有进行新模型训练。在线检测在 FPGA PL；ARM 与电脑工作站负责传输、复核和留证。离线 Python 参考程序独立存放，不能当作上板测试。

V1.53 原工程、历史报告和提交文档保留用于追溯；其板测通过结论、旧 BIT/ELF 与原始 `PACKAGE_MANIFEST.json` 不代表本次 V1.64 的验收。当前入口为 `host/start_single_tile.ps1` 和 `scripts/program_single_tile.py`，不会自动下载历史固件。

数据来源和许可见项目 [数据说明](project/pynq_z2_tile_v1_53/DATA_PROVENANCE_V164.md)。未上传许可未澄清的 HFENet 图片包。
