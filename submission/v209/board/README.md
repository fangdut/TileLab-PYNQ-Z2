# 上板与运行

先按../build/README.md恢复工程到包外独立目录。Windows、Python与NumPy/Pillow、Chrome、Vivado/Vitis2025.2和USB/JTAG驱动。电脑与板端192.168.33.10同网段；网线传图及结果，USB/JTAG下载并按板卡跳线正确供电，电脑HDMI直连外屏并扩展显示。

运行恢复目录start_station.ps1 -VerifyOnly后，运行start_conveyor.ps1。8793完成工位核验，8794运行模拟流水线；显示页/display保持打开。正常自动通过，报警到复核区人工逐件确认，首次确认复核方式后保留。只有一个后端访问板卡。

器件xc7z020clg400-1，100MHz。当前不是现场相机、实体输送带或机械剔除装置。未访问板卡的恢复与测试不能冒充冷启动物理验收。
