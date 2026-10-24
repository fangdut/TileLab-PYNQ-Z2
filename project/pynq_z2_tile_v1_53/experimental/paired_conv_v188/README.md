# V188：共享 DSP 的 32 路卷积集成

本目录把 V187 的共享乘法接入完整整数检测器。实验目标是在 100 MHz 减少普通卷积处理周期，模型、阈值、图像尺寸和最近邻精度均保持不变。**完整检测器 AXI RTL 已通过，完整 HDMI 系统布局布线及上板帧率待验证。已通过连续 HDMI 测试的版本仍是 V179，实测约 8.17 FPS。**

当前候选为冻结源 `../texture_v170/hls/frozen/v170_hls74.cpp`，与 `texture_paired.cpp` 逐字节一致，SHA256 为 `fc82e26ac29ab739725df336229fefd52a61a1da1fab25a19f16bac7b8c9cad4`。

普通卷积每次处理 32 个输出通道。每个乘法计算共享激活的两个有符号 8 位权重乘积，128 个 DSP 乘法单元同时供卷积和原精度最近邻使用。乘积高半部的借位修正先计数、再在每组求和后补回，以减少加法逻辑。深度卷积维持 16 路。

卷积权重在原有 `16×1024×64` RAM 中分占地址 `0..127`、`128..255`，用两个读端口供应两组权重。最近邻阶段重新加载完整 `0..1023` 码本。统一写入位置避免 HLS 自动把权重 RAM 拆成两倍数量的存储体。当前固定模型的普通卷积最多需要 72 个权重字；候选明确拒绝超过 128 个字的普通卷积任务，不能描述为支持任意网络。

已完成：

- 冻结模型的 117 张公开开发集真实图片：评分和原尺寸输出掩膜全部与原参考一致，模型 SHA256 仍为 `1501e32e733b566e17d125613d0989c04291b658459d63b826e418f6f713ed65`。这是 C 算术回归，不是盲测或实板验证。
- 独立标量参考检查实际集成 MAC：158 组、200963 个检查，覆盖有符号极值、空间边界、576 输入通道及 1024 个最近邻码本项。
- HLS74 综合：240 BRAM18、212 DSP；共享乘法函数使用 128 DSP，32 个累加器存储体的复用间隔检查通过。**HLS 的 LUT、寄存器和时序估计不代表实际器件占用或布线时序。**
- 实际生成的 MAC RTL：6种模式连续切换，673个1024位输出包全部一致，1406个输出停顿周期；包括最大576输入通道和1024项最近邻。
- 完整检测器 AXI RTL：采用预先冻结的缩小网络向量，带内存握手等待，连续两次启动共13302个评分、特征及掩膜字一致，第二次正确清除报警和掩膜。该测试不等于117张实拍照片的RTL仿真。
- 检测器本体实际器件综合：48726 LUT、57800 FF、217 DSP、118 BRAM Tile；这是本体综合，完整视频系统资源与布线时序仍需验证。

尚待完成：完整 HDMI 系统布局布线、实板逐值和持续视频验证。任何一项未通过，都不能用理论输出通道数推算新版 FPS。

前两次尝试保留为 HLS72、HLS73：两者 C 回归均通过，但 HLS72 的累加器复用和资源检查失败，HLS73 的存储容量检查失败。它们没有上板，不能作为候选发布。

验证入口：

```powershell
python check_mac.py --out D:/TileBuild/v188_mac_fresh
python check_generated.py --hls D:/Vivado/TileLab_RealPhotos_20261020/v170_hls74 --out D:/TileBuild/v188_structure.json
python synthesize_detector.py --hls D:/Vivado/TileLab_RealPhotos_20261020/v170_hls74 --out D:/TileBuild/v188_ooc_fresh
python test_generated_mac.py --hls D:/Vivado/TileLab_RealPhotos_20261020/v170_hls74 --out D:/TileBuild/v188_mac_rtl_fresh
```

每次选择不存在的输出目录；`test_generated_mac.py --prepare-only` 只准备向量，之后可用同一路径加 `--resume` 执行 RTL。仅对子系统仿真，不能代替完整 AXI 验证。机器内存有限，实际综合与大型仿真应依次执行。

DSP packing 是已有方法，本目录的工作是面向本检测器的数据流、缓存和精确算术集成，不把通用打包方法宣称为原创。自动存储拆分的背景见 [AMD 数组划分文档](https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/Array-Partitioning)。
