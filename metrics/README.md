# 冻结指标与证据来源

`metrics.csv`逐行给出数值、单位、范围、原始文件与JSON字段。来源为V202归档summary.json，与V203材料中的V202_acceptance.json一致。该表不新增测量，也不把开发集统计命名为独立accuracy。

从仓库根目录运行`python metrics/scripts/summarize_v202.py --out runtime_metrics.csv`可离线复算；脚本不访问板卡、不部署、不推理。

| 公开展示值 | CSV字段 | 范围 |
|---|---|---|
| 124.72ms | pl_mean_ms | 117图PL内核均时 |
| 501.79ms | transfer_detection_mean_ms | 117图传图加检测，不含解码、完整UI复核、保存 |
| 1.220s | cycle_mean_s | 100逻辑周期，含0.25s脚本复核等待、API及落盘 |
| 8.02fps | fixed_frame_pl_fps | 固定DDR帧内核微基准，不是新视频 |
| 33正常零误报、84缺陷检出 | normal_false_alarms / defects_detected | 开发集，不外推独立精度 |

资源与时序另引用[历史匹配硬件报告](../project/pynq_z2_tile_v1_53/reports/v179/verified_hdmi_overlap/verification.json)：LUT42482/53200、FF60203/106400、BRAM127.5/140（36Kb等效）、DSP218/220；100MHz setup +0.013ns、hold +0.024ns、DRC0。V202未改该BIT。资源接近上限只说明约束，不证明低功耗或效率领先。

## 日志与逐图证据索引

为保留原始路径与哈希，使用链接索引，不复制或重命名旧日志。

- [冻结测试计划](../project/pynq_z2_tile_v1_53/reports/v202/plan.json)
- [整轮汇总](../project/pynq_z2_tile_v1_53/reports/v202/summary.json)
- [117图逐图记录](../project/pynq_z2_tile_v1_53/reports/v202/exact117_records.json)
- [固定帧记录](../project/pynq_z2_tile_v1_53/reports/v202/core200_summary.json)
- [22次接口与38次拒绝](../project/pynq_z2_tile_v1_53/reports/v202/workflow_summary.json)
- [100周期逐条记录](../project/pynq_z2_tile_v1_53/reports/v202/soak_records.json) · [审计](../project/pynq_z2_tile_v1_53/reports/v202/soak_audit.json)
- [复测前时钟/复位](../project/pynq_z2_tile_v1_53/reports/v202/clock_reset_before.log) · [复测后](../project/pynq_z2_tile_v1_53/reports/v202/clock_reset_after.log)
- [真实良品结果截图](../project/pynq_z2_tile_v1_53/reports/v202/good_report.png) · [真实裂纹结果截图](../project/pynq_z2_tile_v1_53/reports/v202/defect_report.png)
- [历史失败分析](../docs/limitations.md)

截图源于公开MVTec实拍开发照片与实际PL输出；它们不是示波器、逻辑分析仪或整机实拍。本项目没有这些仪器测量时，不为填目录制造波形证据。
