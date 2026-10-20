# V169 实拍瓷砖：完整 PL 推理迁移

本目录是独立的 Zynq-7020 推理工程，目标是把 V168 的电脑实拍检测迁入 FPGA 的可编程逻辑（PL）。早期 HDMI 规则检测器和 V168 CPU 工作站都不能充当本版本的上板证据。

**验收状态以 `reports/v169/acceptance.json` 为准。没有板端报告时，只能称为迁移开发版。**

## 运行分工

| 位置 | 执行内容 |
|---|---|
| FPGA PL | RGB 双线性缩放、归一化、全部卷积与折叠 BN、ReLU、残差、最大/均值池化、双尺度特征组合、PCA64 投影、1024 个正常中心的距离比较、平滑、图像报警、原尺寸二值掩码 |
| 板端 ARM | 裸机以太网、TCP 收发、CRC、缓冲区归属、加速器启动和完成轮询 |
| 电脑运行端 | PNG/JPEG 解码、原始 RGB 打包、网络传输、显示板端结果、保存证据 |
| 电脑离线开发端 | 参考算法、正常特征库标定、模型导出、数值对照；这些不是板端推理结果 |

电脑运行端是 `tools/fpga_texture_v169/board_client.py` 和 `station.py`，没有 Torch、ONNX 或 GPU 推理调用，也不会在开发板断开时换用 CPU 判定。

## 硬件结构与限制

HLS `texture_infer` 一次启动执行完整网络图。特征网络为 WideResNet50-2 的 stem 与 layer1–3；使用预训练权重，BN 在离线导出时折叠进卷积。权重保留 FP32，四路乘加复用片上 RAM；完整模型约 100 MB，工作区约 44 MB，均位于板上 DDR。

新平台以网线输入实拍图片，当前未合并旧 HDMI 接收链路。输入上限 1024×1024，PL 内缩放为 448×448。网络约 367 亿次乘加，首版侧重完整迁移和数值一致，**不承诺视频实时速度**。频率、资源和延迟必须使用实际实现及上板报告，不能以 HLS 目标频率代替。

卷积使用 32 个独立累加槽。连续卷积 tap 每步递增，复用同一槽的间隔为 32 次迭代；HLS 报告的该流水线延迟小于 32 周期，故可声明槽数组没有相邻迭代依赖。RTL 测试含超过 32 个 tap 的卷积，验证累加槽回绕。测试失败时不能生成验收发布包。

## 数据与准确率口径

当前正常特征库来自 MVTec AD Tile：180 张正常建库、50 张正常标定阈值，117 张历史测试图片用于开发评估（33 正常、84 异常，其中 17 张裂纹）。PCA、中心选择和阈值标定均不使用异常测试标签。历史测试集已暴露，不能称为新盲测或实体产线验证。

压缩模型的离线参考结果为 116/117 正确、84/84 异常检出、17/17 裂纹检出、正常误报 1/33。**不能把这组离线数字直接写成 FPGA 实测准确率。** 板端初始验收选择清单中第一张正常图和第一张裂纹图，逐点对照评分图，并校验实际 PL 身份、模型 CRC、输入 CRC、返回 CRC 和全部 59 个网络步骤。

证据目前限于该 Tile 材质，不能宣称任意彩绘、多材质或多砖墙面均通过。新花色需要独立正常标定与独立验证。

## 重建与运行

使用 Vitis/Vivado 2025.2，器件 `xc7z020clg400-1`。每次构建必须选择新的绝对输出目录，不覆盖旧发布镜像。

1. `prepare_model.py` 用固定正常数据生成压缩库；`export_graph.py` 导出 `model.bin` 和 `graph.json`。
   仓库已保存 `models/texture_v169_r1` 冻结配置；也可运行 `rebuild_model.py --profile models/texture_v169_r1 --weights-cache models/cache/wide_resnet50_2-95faca4d.pth --out models/runtime_v169`，从固定来源和校验过的上游权重重建完全相同的模型。此步骤为离线构建，运行端不调用。
2. `make_vectors.py` 生成小型全链路算术测试；设置 `TILE_TEXTURE_HLS`、`TILE_TEXTURE_VECTORS`，用 `vitis-run --mode hls --tcl scripts/texture_v169/build_hls.tcl` 运行 C/RTL 仿真与 IP 导出。
3. 设置 `TILE_TEXTURE_HW`、`TILE_TEXTURE_HLS`，用 Vivado batch 执行 `build_hardware.tcl`。脚本检查仿真、源文件一致性、最终 setup/hold 和 DRC 后才导出 XSA。
4. 设置 `TILE_TEXTURE_SW`、`TILE_TEXTURE_HW`、`TILE_TEXTURE_HLS`、`TILE_TEXTURE_MODEL`，用 Vitis Python 执行 `build_software.py`，生成独立 ARM 传输固件。
5. `program_board.py --hardware ... --software ... --out ...` 校验镜像身份并通过 JTAG 临时加载；不写 Flash。
6. 电脑网卡与开发板直连，板端固定 `192.168.33.10:9135`。`validate_board.py --dataset ... --model ... --out ...` 执行初始真实图片验收。
7. `station.py --dataset ... --model ... --out ...` 在 `127.0.0.1:8789` 提供板端工作站。

断线或 PL 失败会报错。图像缓冲区在 PL 完成前保持独占；不会为了响应新的请求覆盖运行中的输入或模型。

## 许可

原创源码遵循仓库 MIT；AMD/Xilinx 工具及 BSP 保留其原许可。MVTec 图片、掩码和数据派生特征库保留 CC BY-NC-SA 4.0，预训练权重保留上游条款。不能把第三方数据或派生模型统一标为 MIT。
