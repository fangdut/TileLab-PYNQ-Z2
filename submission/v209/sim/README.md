# 仿真与验证导航

恢复后的工程verified_hdmi/hls/accepted_export.zip含接受的HLS导出；verified_hdmi/source/experimental/目录含C++测试台及RTL仿真。project/reports/保留原始数值、协议和流程验证记录。

最新流水线离线保护测试：在恢复目录project/host/conveyor_station执行 `python -m unittest -v test_flow.py test_policy.py test_station_api.py`。18项不访问板卡。新增通用技能复用测试见../skill/verification.json，不与板测统计混用。
