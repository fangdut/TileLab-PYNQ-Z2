# V170 全整数 FPGA 实拍检测候选

本目录的 C++ 是可综合 HLS 源码，生成的 Verilog 运行于 Zynq-7020 PL。Python/Torch 只用于离线方案设计、正常样本标定与核对。运行时电脑只解码文件、封装 RGB、传输、显示；ARM 只处理 TCP、CRC、缓冲区所有权、配置与计时，没有图像检测后备。

PL 执行有理数双线性缩放、定点归一化、MobileNetV2 第 0–13 层的 INT8 卷积/深度卷积/残差、整数池化和插值、INT16 特征投影、正常码本搜索、整数平方根、平滑、图像判定与原尺寸掩膜。模型采用 PCA64、1024 个正常码字，224 输入的完整二进制为 751,760 字节。卷积后处理使用 signed24 输入，导出器用 `127*sum(abs(weight))+abs(bias)` 对非零整数倍率的输出通道证明无溢出；倍率为零的通道输出恒为零。

冻结模型在 `../../models/texture_v170_r1/`。347 张原始照片的来源和 SHA256 位于其中的 dataset_manifest.json；180 张正常图建立特征库，另外 50 张正常图确定阈值。历史测试集为 33 张正常、84 张异常，其中 17 张裂纹。该集合被用于方案比较，属于开发基准，不是独立盲测。

224 整数候选的图像级开发结果为 117/117。**这不是像素级精度，也不意味着任意花色都已验收。** 另测的异常图平均掩膜 IoU 约 0.519，裂纹平均 IoU 约 0.067，说明裂纹范围仍偏粗。不得用“C++ 掩膜逐点一致”替代与真实标注的定位精度；前者只是实现数值一致性。

## 构建

工具链为 Vivado/Vitis 2025.2，目标 xc7z020clg400-1。使用新的绝对输出目录，避免覆盖旧证据。以下路径从工程根目录计算。

```powershell
$env:TILE_TEXTURE_VECTORS='D:/Vivado/your_vectors'
python tools/fpga_texture_v170/make_vectors.py --out $env:TILE_TEXTURE_VECTORS
$env:TILE_TEXTURE_HLS='D:/Vivado/your_hls'
& D:/2025.2/Vitis/bin/vitis-run.bat --mode hls --tcl scripts/texture_v170/build_hls.tcl
$env:TILE_TEXTURE_HW='D:/Vivado/your_hardware'
& D:/2025.2/Vivado/bin/vivado.bat -mode batch -source scripts/texture_v170/build_hardware.tcl
$env:TILE_TEXTURE_MODEL=(Resolve-Path models/texture_v170_r1).Path
$env:TILE_TEXTURE_SW='D:/Vivado/your_software.sdk'
& D:/2025.2/Vitis/bin/vitis.bat -s scripts/texture_v170/build_software.py
python scripts/texture_v170/program_board.py --hardware $env:TILE_TEXTURE_HW --software $env:TILE_TEXTURE_SW --out D:/Vivado/your_program_evidence
```

下载前检查 RTL 协同仿真、实际复位连接、时序、BIT/XSA/ELF 和模型哈希。只通过 JTAG 易失加载，不写 Flash。`hls/frozen/v170_hls10.cpp` 保留已经通过 RTL 的并行基线；构建器按 HLS 输出目录同名快照严格核对字节。HLS15 已完成 117 张实板逐数值验证，自动重启 4.279 FPS；同名冻结源码与最新完整包可复现。HLS18 的 DSP 复用通过 RTL，当前 HLS19 进一步改 DDR 行突发，均须独立完成实板验证。

## 运行与验证

电脑有线网口为 192.168.33.30/24，开发板为 192.168.33.10:9136。运行依赖只有 Pillow、NumPy，部署不需要 Torch。

```powershell
python tools/fpga_texture_v170/board_client.py --model models/texture_v170_r1 --image path/to/original_photo.png --out D:/Vivado/new_case
python tools/fpga_texture_v170/station.py --dataset path/to/dataset --model models/texture_v170_r1 --out D:/Vivado/station_records --port 8789
```

文件原图须在 1024×1024 以内，不在电脑端缩放。协议校验实际 PL 身份 0x17000001、启动身份、模型 CRC、原图 RGB CRC、结果 CRC 和完整任务数。工作站收到错误就显示失败，没有 CPU/GPU 兜底。

`validate_board.py` 在匹配程序身份下检查冻结测试图的原图、整数评分、原尺寸掩膜和帧号；随后启动 PL auto-restart 固定帧微基准。连续运行只发出一次 ARM start，使用 PL 的完成帧计数计时，停止时等待在途帧排空。**固定 DDR 图片循环的核内 FPS 不代表持续 HDMI 新帧 FPS。** 网线输入与返回约 5.6 MB/张，在当前 100 Mbps 链路上也不能等同核内实时速度。

连续 HDMI 采集、PL 缓冲区所有权/调度、独立新样本泛化和细裂纹定位仍是后续验收项。目标先达到持续 10 次检测/秒，再进一步提速，不预先承诺测量结果。

原创源码采用 MIT。MVTec 派生模型、配置、照片和评估证据保留 CC BY-NC-SA 4.0，预训练权重和厂商 IP 保留原许可。
