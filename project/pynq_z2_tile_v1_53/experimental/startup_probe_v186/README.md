# V186 启动阶段标记（诊断固件，未验收）

此固件只为定位板端启动故障，尚未下载或验证。正常检测固件及模型保持不变；不得把本编译结果当成新版检测或吞吐验收。

使用 SLCR REBOOT_STATUS 的软件保留高8位记录启动阶段，保留低24位硬件/BootROM状态。0xA1/A2为关闭DCache之前/之后，A3/A4为启动编号读取之前/之后，A5/A6为PL身份读取之前/之后，A7为DDR内存属性设置完成，A8/A9为网口初始化前/后，AA为TCP监听就绪；E1/E2/E3为启动编号、PL身份、网口错误。此路径不计算图像。

`main_debug.c` 已针对V186匹配的125MHz BSP成功编译。原始构建及USB恢复失败记录位于 `../../reports/v186/coldboot_recovery04/`。2026-10-23用户已断电重启；首次JTAG扫描恢复了APU，但Windows USB接口B仍为Code10，后续新扫描无设备；软件驱动重启被操作系统拒绝，FTDI按序列号打开也失败，目前等待USB数据线重新插拔。

通过Vitis脚本设置TILE_TEXTURE_BSP（此前匹配软件目录）、TILE_TEXTURE_SW（新的输出目录）、TILE_TEXTURE_HW（V186硬件目录）和TILE_TEXTURE_MODEL（冻结模型目录），运行 `vitis.bat -s build_debug.py`。原工程BSP的BIT/XSA/模型身份必须相符。编译不执行任何下载。诊断器件寄存器依据AMD UG585的Reset Reason章节，软件高8位仅在非POR复位中保留。
