# V208工程复现

## 获得完整目录

使用随附V208 ZIP或RAR解压到独立目录；压缩包不是通过改后缀转换。公开仓库也可重建相同目录：

```powershell
git clone --branch fpga-real-texture-v170 https://github.com/fangdut/TileLab-PYNQ-Z2.git
cd TileLab-PYNQ-Z2
python tools/build_v208_bundle.py --out ..\TileLab_V208
cd ..\TileLab_V208
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_station.ps1 -VerifyOnly
```

源映射逐文件核对SHA256和路径，离线校验同时检查BIT/XSA/ELF/模型配对、时钟复位和已验收时序，不访问板卡。完整Git克隆需取得版本资产；浅层只下载文档不够。此工具是按固定版本装配，不重新综合硬件。

## 环境与启动

Windows、Python与NumPy/Pillow、Chrome、Vivado/Vitis2025.2及USB/JTAG驱动；可用TILELAB_PYTHON、TILELAB_XSDB、TILELAB_CHROME覆盖安装路径。电脑与板端192.168.33.10同网段，USB/JTAG供下载，按板卡跳线正确供电，电脑HDMI直连外屏并扩展显示。

双击“启动流水线.cmd”。首次部署会JTAG易失下载，不写Flash。已有匹配检测服务时复用其配置。任何时候只由一个后端访问板卡。

先在8793选择已部署纹理砖参照，按真实的公开照片回放条件完成3张不同良品加1张已知缺陷核验并封存。这不是训练或独立准确率认证。再在8794选01/02/03、4秒区域时间，启动队列；未报警自动通过，裂纹到右侧后人工复核。显示页/display负责截帧，不能关闭。

## 检查与停止

原图保持原生像素，不按预设标签产生判定。核对源帧指纹、模型、启动编号、FPGA帧号、掩膜和处置类型。自动通过review为空；人工意见另存。截图至应用的时间与内核、历史传图均值分别比较。

在project/host/conveyor_station运行 `python -m unittest -v test_flow.py test_policy.py test_station_api.py`，18项不访问板卡。主动浏览器回放另需Playwright、Chrome与ffmpeg，脚本会操作工件并标注非人工。正式本人录制不运行验收脚本。

“本块后暂停”完成当前工件后停止下一块。停止服务前保留runtime记录并完成工件；录制重开脚本会保存旧状态，明确弃用未完成工件，不伪造复核。恢复后应重新检查板端身份。不要删除记录以掩盖失败。

本次V208包完成新目录装配、文件哈希/部署配对校验和18项离线测试；没有宣称在另一台机器冷启动上板验收。原V202与V207实板证据分别保留。
