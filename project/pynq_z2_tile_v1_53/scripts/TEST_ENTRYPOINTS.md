# 当前验收入口

Python 主机单元测试 `python -B -m unittest discover -s host -p "test_*.py" -v`；前端 5 组 Node 脚本见根 README；原生播放器解析 `test_stimulus_command_native.py`。

| 当前脚本 | 环境与副作用 |
|---|---|
| activate_current.py | 停止工作站后才可运行；核对继承二进制和随包基线清单；XSDB 下载易失配置 |
| wait_board_ready.py | 核对当前下载登记、固件、启动号和完整输入；只读板端状态 |
| board_v153_real.py [--wide] | 50 张历史实际照片，切换 HDMI，临时独占 TCP；引用随包 masks 和 validation/reference_rgb |
| board_v153_holdout.py | 24 张 MCS2 初测；工程计算一致性不代表跨材质检测通过 |
| board_v153_transport.py | 同事件 RAW/RLE/PACK 三格式；实际 RST 中断后重新取未确认事件 |
| board_v153_helpers.py --loopback | 临时本地 HTTP/TCP、故意延迟；不接真实板卡 |
| board_v153_helpers.py --board | 实板诊断与暂停、真实手动留图；最后暂停并回空传送带 |
| board_submission_acceptance.py | 120 秒连续运动、自动最佳帧与存档校验；最后恢复仅预览 |
| collect_submission_evidence.py | 汇总通过/失败的实测事实，不控制开发板 |
| verify_submission.py | 对冻结文件进行内容哈希检查，不控制开发板 |

结果目录不存在时才能创建；旧目录请明确改名保存，不能覆盖失败记录。一次只运行一个实板测试。还未完成真实相机、24 小时工厂压力或物理 HDMI 热插拔验收。

`v1xx` 历史准备、创建和封版脚本保留为开发来源，不是本版的一键入口。它们可能引用历史目录，应在明确的研究副本中使用。`run_tests.ps1` 是早期 V0.4 自检，不能单独代表本版验收。当前 RTL 沿用 V1.52 双尺度实现：`prepare_dual_scale_v152.py`、`test_dual_scale_v152.tcl` 与 `prepare_integrated_v152.py`、`test_integrated_v152.tcl`。
