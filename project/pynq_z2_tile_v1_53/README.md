# TileLab：FPGA 瓷砖裂纹候选检测与证据复核

V1.53 最终提交候选，PYNQ-Z2 / xc7z020clg400-1，Vivado 与 Vitis 2025.2。

本项目把连续 HDMI 输入中的暗裂纹候选识别放在 FPGA 内。瓷砖经过视野时，电路产生局部红框并选出完整、接近中央的缺陷证据；ARM 将同帧原图、掩码、产品号、参数和校验值传给电脑，电脑负责限额存档与人工复核。

**实际范围：已经标定的纹理瓷砖竞赛原型。** 输入使用公开真实照片加合成运动，尚未接工业相机，也未在真实工厂验收。不是 YOLO，不是通用材质检测器，红框表示需要人工复核的候选。

## 三个交付部分

| 部分 | 已实现产品与分工 |
|---|---|
| Vivado / FPGA | 720p60 HDMI 收发、灰度、半径 8/16 对向暗谷、双阈值与四级邻域支持、32×32 网格区域、最多 8 个局部框、产品跟踪、最佳帧与 CRC |
| Vitis / ARM | 裸机 DMA/DDR 帧槽管理，最多 12 个待确认事件、48 个帧槽，无损 RAW32/RLE/PACK25、TCP 9133、应用确认、身份和采集恢复管理 |
| 电脑工作站 | 浏览器预览、事件优先取图、默认 2 fps 普通预览、按产品留证、容量上限、SQLite 复核、文件 SHA256、并发修订检查、HDMI 测试播放器 |

**算法主要在 PL。** ARM 和电脑不代替电路计算裂纹。`models/` 里的 NumPy 算法仅用于离线验算，不在运行工作站中执行识别。

## 当前实板结果

| 验证 | 实际结果与范围 |
|---|---|
| 历史真实照片回归 | 窄/双尺度各 50 张，17 张裂纹报警、33 张正常零报警；像素、区域与参考计算一致 |
| 弱裂纹像素召回 | 26.37% → 28.20%；双尺度像素精确率 98.36%。反复使用的开发集，不能称独立工业准确率 |
| 连续移动与最佳帧 | 120 秒，20 条不同产品完整证据，约 60 fps 输入，源帧码测得最大居中误差 14 px；原图/掩码/CRC/存档 SHA256 逐条核对 |
| 传输 | 50 组同事件 RAW/RLE/PACK 请求逐字节一致，实际中断 TCP 后同一未确认事件可重取；噪声 PACK25 少 21.875% 字节，但未更快 |
| 软件 | 431 项 Python 单元测试；5 组实际前端脚本测试、原生 WPF 命令解析、真实板端诊断与受控延迟 TCP 回环检查通过 |
| 外部材料初测 | MCS2 的 24 张大理石裂纹图，仅 1 张报警，像素召回约 1.92%。计算一致性通过，跨材质识别能力未通过 |

全部数值以 `reports/v153/final_validation_summary.json` 为准。不能把像素精确率写成“准确率 98%”，也不能把输入 60 fps 写成电脑每秒存 60 张全图。

硬件与 ARM 下载产物继承已布线 V1.52，并已在 V1.53 主机环境中实际下载测试。V1.53 新建的 XPR、Block Design 和生成目录是真实 Vivado 工程，但没有声称重新完成了一次新的硬件布局布线。BIT/XSA/ELF 哈希及来源见 `DELIVERY_MANIFEST.json`。

## 目录

```text
pynq_z2_tile_v1_53.xpr             Vivado 工程
rtl/ constraints/ ip_repo/        电路、板级约束、HDMI IP
scripts/create_project.tcl        从零构建 Block Design 和硬件
scripts/rebuild.tcl               在生成的工程中重建
pynq_z2_tile_v1_53.sdk/            Vitis workspace；平台、应用、构建与下载入口
  ethernet_sources/              ARM 应用的权威源码
  system.bit system.xsa system.ltx
  hdmi_ethernet/build/hdmi_ethernet.elf
host/                            实际工作站、播放器和测试
models/ sim/                     离线参考和 RTL 自检
data/                            测试输入、真值、来源与许可
validation/reference_rgb/        50 张历史实际 HDMI RGB 对照图
reports/v153/                    实测摘要与过程证据
docs/                            两份 PDF 与可编辑生成源码
```

## 接线与启动

1. 电源按板卡标识连接。需要改变启动跳线时先断电，按官方板卡手册选择 JTAG 启动。
2. 电脑 HDMI OUT → 板卡 **HDMI IN**；板卡 **HDMI OUT** → 显示器 HDMI IN。共两根 HDMI 数据线。
3. 板卡 **PROG UART Micro-B USB** → 电脑。USB 数据线必须能枚举 FTDI/JTAG；COM 号以当前设备为准，不能硬编码 COM20。
4. 板卡 RJ45 → 电脑网口，用 Cat5e/Cat6 网线。电脑与板卡必须同网段、地址不冲突。本机已经使用电脑 `192.168.33.30/24`、板卡 `192.168.33.10`；其他机器不要盲目照抄。
5. 将输出到板卡的扩展显示设为 **1280×720、60 Hz**。播放器要求恰好一个非主屏且分辨率为 720p；它显示的是没有预画红框的输入图。
6. 先停止本项目服务，再下载易失配置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File host/stop_station.ps1
python -B scripts/activate_current.py 192.168.33.10
python -B scripts/wait_board_ready.py
powershell -NoProfile -ExecutionPolicy Bypass -File host/start_station.ps1 -Ethernet 192.168.33.10
```

Python 3.10+，运行依赖 `python -m pip install -r host/requirements.txt`。网页是电脑本机 `http://127.0.0.1:8770/`。也可直接运行 `.sdk/program_ethernet.bat <板卡私网IPv4>`，其入口会检查 XSDB 错误；下载不是写入永久启动存储，断电后需要重新下载。

网页先“开始采集”或“读取板端状态”，确认固件 `0x12b00` 和完整帧健康，再在空传送带时选“双尺度弱裂纹增强”，输入选“真实照片合成流水线”。配方在产品间隙生效，应同时看请求值与实采值。默认**仅预览**，不会无限保存自动事件；需要正式留证时改为自动留图并设置容量上限。

## 构建与迁移

当前机器工具安装在 `D:/2025.2`。其他机器需要在所列批处理/脚本中修改工具路径，或用其安装目录的工具执行同一 Tcl/Python 入口。

- 保留项目文件夹名 `pynq_z2_tile_v1_53`。整个 `.sdk` 是 Vitis 工作区，不要将项目根当 workspace。
- 移到其他目录后，先执行 `python -B scripts/relocate_project.py` 更新生成的项目/工作区路径；不修改权威 RTL、ARM 源码或接受的下载二进制。
- 在**复制的构建工程**运行：`$env:TILE_RECREATE='1'`，然后 `D:/2025.2/Vivado/bin/vivado.bat -mode batch -source scripts/create_project.tcl`。生成过程会暂存 `.sdk`，防止 Vivado `-force` 清掉软件工作区。
- 仅需要重建工程结构可再设 `$env:TILE_PREPARE_ONLY='1'`；这不生成新的综合/实现证据，不能称时序通过。
- 实现完成、检查建立/保持时序及 DRC 后，执行 `D:/2025.2/Vitis/bin/vitis.bat -s pynq_z2_tile_v1_53.sdk/build_vitis.py`。用 `.sdk/open_workspace.bat` 打开 IDE。
- 新构建可能改变调试路径/二进制哈希。冻结版本的 `activate_current.py` 会拒绝不匹配的产物；新构建必须作为新的候选重新检查、下载、验收与登记，不能沿用旧实测报告。

## 测试入口

```powershell
python -B -m unittest discover -s host -p "test_*.py" -v
node scripts/test_review_session.js
node scripts/test_preview_ui.js
node scripts/test_inventory_ui.js
node scripts/test_status_ui.js
node scripts/test_display_ui.js
python -B scripts/test_stimulus_command_native.py
python -B scripts/board_v153_helpers.py --loopback
```

实板测试要求当前项目服务运行、配套二进制已下载。测试会临时切换输入、参数和采集状态；不要与其他硬件测试并行。以下脚本拒绝覆盖已存在的结果目录，重测时先将旧目录改名保存。

```powershell
python -B scripts/board_v153_real.py
python -B scripts/board_v153_real.py --wide
python -B scripts/board_v153_holdout.py
python -B scripts/board_v153_transport.py
python -B scripts/board_v153_helpers.py --board
python -B scripts/board_submission_acceptance.py
```

`scripts/TEST_ENTRYPOINTS.md` 列出当前和历史入口。历史 `v1xx` 的创建/最终化脚本用于溯源，不应再次运行来改变冻结版。当前双尺度 RTL 自检由 `prepare_dual_scale_v152.py` / `test_dual_scale_v152.tcl` 和 `prepare_integrated_v152.py` / `test_integrated_v152.tcl` 提供。

## 已知限制与下一步

1. **最优先是弱裂纹与跨材质。** 没有强种子的低对比裂纹无法靠四轮邻域补全解决。低阈值的外部实验误报很多，未加入默认配方。下一步固定成像、分材质开发/独立正常与缺陷产品集，再验证方向线支持、局部归一化。
2. HDMI 直通红框使用上一帧统计，电脑存档使用同帧坐标；快速运动时二者视觉位置存在区别。
3. 队列与 DDR 都有界，停止取图太久会丢失，板卡断电不能保证未传事件留存。尚未完成 24 小时、真实 HDMI 拔插或工厂可靠性认证。
4. 本版已布线 WNS +0.030 ns、WHS +0.050 ns，BRAM 74.64%。应先量化瓶颈，不能直接提频；720p 像素时钟也不能任意更改。
5. 裁剪 ROI + 全帧缩略图可进一步减少传输，但必须保持坐标、原图、掩码和身份一致；目前未实现。
6. 工业化还需要相机/光源、独立产品测试、权限审计、断电留证和剔除执行机构。

## 文档和第三方素材

- `docs/TileLab_最终提交版_技术与教学手册.pdf`：产品、原理、公式、时钟/CDC、DMA、传输、存档、源码路线、术语教学与答辩。
- `docs/TileLab_演示视频详细拍摄方案.pdf`：建议 4:30 成片、逐镜头、接线、手机与录屏、讲解稿、字幕、检查和补拍。实际时长要求以比赛提交页为准。
- 数据来源、衍生处理和许可见 `data/DATA_SOURCES.md`、`THIRD_PARTY_NOTICES.md` 与各素材许可文件。MVTec 图片和衍生图仅用于非商业研究，CC BY-NC-SA 4.0；MCS2 是 CC BY 4.0。公开仓库不改变第三方许可。
- 发布包不包含运行中的复核数据库、用户备注、PID、海量自动截图或工具缓存。代表性实测证据保留，旧工程备份独立保存。
