# TileLab V208完整工程

默认功能：电脑模拟瓷砖输送，进入检测区即从canvas取原生像素帧，经网口送往冻结V202 PL检测。未报警自动通过，异常或结果迟到在右侧复核区停止。当前不是HDMI取帧检测；外屏由电脑HDMI直连，扩展模式显示。

先用 start_station.ps1 -VerifyOnly 校验所有文件及冻结部署配对；双击“启动流水线.cmd”启动。需要Windows、Python与NumPy/Pillow、Chrome、Vivado/Vitis2025.2及板卡驱动。TILELAB_PYTHON/TILELAB_XSDB/TILELAB_CHROME可指定路径。USB/JTAG与网线连接板卡，电脑与192.168.33.10同网段。首次启动会易失下载，不写Flash。

首次在8793页面建立材质，按公开照片回放条件完成3良品加1缺陷核验并封存；再在8794启动队列。单次复核方式确认保留，正常自动通过不写人工意见。正式拍摄不运行accept_continuous.cjs。

原start_station.ps1与“启动检测.cmd”保留为核验入口。流水线代码见project/host/conveyor_station；报告见report。核验与显示完整操作见该目录README。只有一个服务访问板卡，不另开推理客户端。

V202 BIT/XSA/ELF/模型哈希保持原值，新增的是电脑软件、文档与启动集成。报告已纳入参赛者提供的三张设备实拍与现场页面截图，并区分显式自动回放证据。参赛者已提供剪辑后的演示视频用于官网提交；中英文海报和正式作品名称已同步。视频未公开到代码仓库。图片与派生参照保留非商业/相同方式共享许可，原创代码MIT，厂商内容保留原条款。
