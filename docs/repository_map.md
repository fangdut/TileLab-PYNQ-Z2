# 仓库目录与评审入口对照

初级赛道使用官方五部分Word模板。具身智能截图的推荐目录用于改善可读性，不作为强制结构；本次保留工程路径，通过文档映射给出同等查阅入口。

| 推荐类别 | 本仓库实际位置 | 说明 |
|---|---|---|
| README | 根目录README.md | 当前版本、数据和复现入口；历史另存 |
| docs | 根目录docs/ | 架构、通信、接线、模型、复现及局限 |
| fpga/src | project/pynq_z2_tile_v1_53/experimental/texture_v170/hls/frozen/v170_hls62.cpp；experimental/video_v171/ | 冻结核与已有视频链路，路径以前述project为根 |
| fpga/build | project/pynq_z2_tile_v1_53/scripts/texture_v170/；deliverables/V179_Verified_HDMI_8p17FPS_Dev.zip | 构建脚本与历史冻结基线，不冒充V202完整ZIP |
| fpga/report | project/pynq_z2_tile_v1_53/reports/v179/、v200/、v202/ | 实现、传输控制和有限复测证据 |
| host/model | project/pynq_z2_tile_v1_53/models/texture_v170_r1/；V202包profiles/ | 冻结模型和双参照 |
| host/app | project/pynq_z2_tile_v1_53/host/stop_inspect_station/ | 工作站与复核流程 |
| host/deploy | 同上deploy_workstation.py；V202包start_station.ps1 | 易失部署与环境检查 |
| metrics | 根目录metrics/ | CSV、来源字段、日志及脚本索引 |
| report | project/pynq_z2_tile_v1_53/reports/v205/ | 当前Word及本次修订记录 |
| skill | project/pynq_z2_tile_v1_53/skill/ | 历史内容保留，不虚增加分项 |

本地engineering_delivery_20261027和competition_materials_20261029是交付归档，不代表均已上传GitHub。V202 ZIP、V204海报本地保存边界在README与复现文档中明确说明。运行工程V202、报告V205、视频脚本V203和海报V204各自版本独立。
