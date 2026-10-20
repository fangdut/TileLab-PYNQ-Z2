# TileLab V1.64：单片瓷砖工程候选

**最新V166进展：** [参照差分改进与实板验证](README_REFERENCE_V166.md)、[当前状态](reports/v166/STATUS.json)、[图文报告](reports/v166/reference_report.html)。本页后续V164离线结果为历史快照；本轮已完成独立窗口算术实板自检及V164检测器的50张HDMI回放，并修复了无外接显示器时的热插拔与PNG取图校验问题。完整V166参照视频算法与目标材料独立准确率仍未验收。

本阶段目标是单片彩绘／多材质瓷砖检测。当前可运行的检测内核仍是 V159 冻结的纹理瓷砖候选，**未达到彩绘／多材质高准确率验收条件**。本项目提供完整源代码、固定单片配置、工作站、离线回归、RTL 仿真和匹配硬件／固件的构建及下载入口。当前实际完成状态以 `reports/v164/QUALIFICATION.json` 与 `releases/v164/DEPLOYMENT.json` 为准。

## 当前结果与范围

| 输入与评估方式 | 裂纹定位图数 | 正常图误报 | 像素精确率 | 像素召回率 |
|---|---:|---:|---:|---:|
| 历史 HDMI 实采图，开发集 OOF，新完整单片 ROI | 17/17 | 0/33 | 96.20% | 65.35% |
| 同批原始 HDMI 输入照片，开发集 OOF，新完整单片 ROI | 16/17 | 2/33 | 87.55% | 60.13% |

两组都是反复使用过的开发样本，17 张裂纹、33 张正常图，不是独立盲测。按原图 ID 划分折，整张测试源图不参与该折拟合；结构与参数仍在这个开发集上选择。历史实采最弱裂纹像素覆盖只有 **2.68%**。不能把整图报警或像素精确率称为通用“准确率”，也不能将 0/33 解释为真实误报率为零。

输入域差异、细裂纹漏分以及彩绘和多材质缺少独立验证，是当前明确的未解决问题。见 `reports/v164/validation.html`。没有本次 V164 的实板验收，没有国奖水平保证。

## 工程与工作边界

- 开发板 PYNQ-Z2，器件 `xc7z020clg400-1`。输入是 HDMI 1280×720、60 Hz；单片表面固定落在 `[390,110]—[889,609]`，共 500×500 像素，四周为固定暗背景。必须人工确认完整表面在这个视野内，当前不自动定位或检查瓷砖数量。
- 检测整个声明的单片 ROI，没有为提高成绩暗中缩边。砖缝、墙面、多砖、任意拍摄角度与任意光照未纳入当前支持范围。
- PL 执行灰度谷值、方向均值、四级局部支持、14 特征／256 棵深度 3 的 Q16 整数树，以及区域证据筛选。复用已有冻结模型；本次没有新训练。高阈值 90、分类阈值 32768、分数门槛 -393216、3×3 支持至少 5 点。
- ARM 负责 DMA、事件队列和以太网。电脑工作站接收 PL 原图、掩码、坐标，执行 CRC、身份、存档和人工复核；不在在线链路使用 Python 重新识别。
- 固件版本 `0x13200`，PL 模型 ID `0xd06b3b9b`，单片配置 ID `0x32b11135`。每次配置／抓拍在当前连接上重新检查模型与单片合同，旧固件、错模型、错 ROI 和启动身份切换会被拒绝。ROI GPIO 回读证明请求寄存器，不能替代逐帧像素域 ROI 生效证明；每张图还检查实际配置与越界掩码。
- “无候选报警”不表示良品合格。当前 UI 保留复核标记与误报记录。

## 安装与离线运行

在本项目目录打开 PowerShell。Python 3.12 已验证，运行依赖只有 NumPy、Pillow，无需训练框架。

```powershell
python -m pip install -r host/requirements.txt
python scripts/check_single_tile_sources.py
python tools/single_tile/detector.py validation/reference_rgb/real_000_original.png --out build_local/offline_000
```

输出 `input.png`、`mask.png`、`overlay.png` 和 `result.json`。不接板可运行此软件参考，但这不验证 HDMI、DMA、时序、资源和真实光学成像。

任意输入必须已是固定的 720p 单片画面。如果仅有一张正方形的单片表面裁图，可以显式传 `--fit-single-tile` 缩放到 500×500 并放入固定画布；非正方形、墙面和含背景裁图会被拒绝。这是明确的重采样适配，不能当作相机实验或通用材质验证。

可选 C 加速器，Windows 示例（编译器使用自己安装的 GCC 路径）：

```powershell
python tools/single_tile/build_native.py --compiler C:/toolchain/bin/gcc.exe --out build_local/integer.dll
python tools/single_tile/detector.py validation/reference_rgb/real_000_original.png --native-library build_local/integer.dll --out build_local/native_000
python tools/single_tile/evaluate.py --input-kind historical_acquired --native-library build_local/integer.dll --out build_local/oof_acquired
python tools/single_tile/evaluate.py --input-kind stimulus --native-library build_local/integer.dll --out build_local/oof_stimulus
```

Linux 可用 GCC 编译 `.so`；不传 `--native-library` 时使用纯 NumPy。折模型仅供 OOF 复现，在线／默认离线使用 `models/v159_integer_model.json`。

## 构建匹配的硬件和 ARM 固件

已安装 Vivado／Vitis 2025.2。所有命令在本项目目录执行。选一个不存在的独立构建目录与不存在的 `.sdk` 工作区；不覆盖历史工程，不自动连接板子。

```powershell
python scripts/prepare_single_tile_build.py --out D:/TileBuild/SingleTile01
Push-Location D:/TileBuild/SingleTile01
& C:/AMD/2025.2/Vivado/bin/vivado.bat -mode batch -source scripts/build_single_tile.tcl
Pop-Location
$env:TILE_SINGLE_HARDWARE='D:/TileBuild/SingleTile01/reports/v164/hardware_run01'
$env:TILE_SINGLE_WORKSPACE='D:/TileBuild/SingleTileSoftware01.sdk'
& C:/AMD/2025.2/Vitis/bin/vitis.bat -s scripts/build_single_tile_software.py
python scripts/package_single_tile.py --hardware $env:TILE_SINGLE_HARDWARE --workspace $env:TILE_SINGLE_WORKSPACE --out build_local/deployment
python scripts/program_single_tile.py --bundle build_local/deployment
```

最后一步只检查，不下载。构建会检查冻结 RTL 哈希，启用生产用无 ILA 配置以节省资源；若时序、DRC 或匹配检查失败则停止导出。打包检查 XSA 内嵌 BIT 与独立 BIT 一致，检查 ELF、源文件、单片配置及 SHA256。保留每次构建的报告，不用旧报告替代。

## 上板与工作站

先关闭开发板电源，按开发板说明选择 JTAG 启动，再接通 PROG-UART 数据线、HDMI 输入和网线并供电。电脑 HDMI 输出设置为 1280×720、60 Hz、扩展显示，确认该输出实际连接开发板 HDMI IN。UART 115200 8N1 可看启动信息；网络默认直连地址 `169.254.200.10`，电脑需在同一链路，或下载时显式用 `--address dhcp` 后读取实际地址。

```powershell
python scripts/program_single_tile.py --bundle releases/v164 --program --xsdb C:/AMD/2025.2/Vitis/bin/xsdb.bat
powershell -NoProfile -File host/start_single_tile.ps1 -Ethernet 169.254.200.10 -Python python
```

只有显式 `--program` 才会进行易失 JTAG 下载；下载前关闭工作站并处理待确认事件。不会写 QSPI。编程后核对固件、启动 ID、PL 模型和单片 ROI 寄存器；通过这些检查也不等于准确率验收。

网页只绑定 `127.0.0.1`，默认端口 8770。可预览、抓拍、无损传输、留图、复核和导出，配方与阈值已冻结。若需要播放仓库里的 HDMI 历史测试照片，在确认第二显示器就是板子输入后，另开 PowerShell 执行 `host/hdmi_display.ps1`，从网页选 17 张裂纹／33 张正常单片或空视野。它会在第二显示器显示测试图；播放器身份与显示状态不等于开发板收到的 HDMI 内容，必须看板端实际返回图。

## 回归验证

```powershell
python -m unittest discover -s host -v
python -m unittest discover -s tools/single_tile -p test_reference.py -v
python -m unittest discover -s tests -v
python scripts/test_single_tile_firmware.py --compiler C:/toolchain/bin/gcc.exe --out build_local/firmware_test
$env:TILE_SIM_OUT='D:/TileBuild/SingleTileCore01'
& C:/AMD/2025.2/Vivado/bin/vivado.bat -mode batch -source scripts/test_selected_v159.tcl
```

当前在线合同、重连、越界拒收和旧版工作站共 485 项测试，484 通过、1 项可选原生解码器检查跳过；另有整数参考与部署防错检查。真实 C 源码片段的 MMIO 桩测试覆盖 28,672 个请求参数组合。具体运行证据见 `reports/v164`；桩测试与 RTL 仿真都不能冒充本次板测。

## 目录与后续目标

`config/` 是单片合同；`rtl/` 为冻结 PL 源码；`pynq_z2_tile_v1_53.sdk/ethernet_sources/` 是当前 ARM 源码；`host/single_tile_station.py` 为当前在线入口；`tools/single_tile/` 是独立离线工具；`releases/v164/` 仅存匹配新构建产物；`reports/v164/` 是当前证据。

目录名与旧 SDK 部分二进制沿用历史工程，旧 `system.bit`、旧 ELF、`reports/v153`、`reports/accepted_baseline` 和上级 `submission_documents` 都是历史留档，不能作为本版下载入口或验收依据。旧入口 `scripts/activate_current.py` 与 `host/start_station.ps1` 已转到新版本受检入口。

使用者已确认按花色做良品参照标定。V165分支新增离线参照原型与独立整数差分RTL，见 [参照原型说明](README_REFERENCE_V165.md) 与 [当前报告](reports/v165/reference_report.html)。完整板端接入、同花色真实良品／裂纹配对和高准确率验收尚未完成。V164下载包与历史验证不包含新参照算法；之后才扩展多砖墙面，再决定是否训练新模型。
# 当前版本：V1.67.2完整参照工程

入口与重新构建请见[当前版本说明](README_REFERENCE_V167.md)，设计报告位于[reports/v167](reports/v167/design_report.pdf)。完整HDMI/DDR/PL差分链路已上板验证，配准和区域分析在电脑运行。实体瓷砖准确率尚未独立验收。以下保留历史版本说明。

