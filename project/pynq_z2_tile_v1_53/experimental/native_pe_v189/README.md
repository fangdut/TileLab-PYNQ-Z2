# V189 独立原生 RTL 实验，未接入检测器

`shared_mac.v` 从原始激活、中心和查询总线计算卷积双路乘积或最近邻平方和，采用六个使能时钟阶段。独立 Python 整数参考和 C 模型核对2048组，RTL核对1998组，另50组按复位协议清空，覆盖580个停顿周期。

`v189_unit_synth01` 的实际独立综合为26269 LUT、15157 FF、103 DSP。综合没有保持实验要求的128个 DSP，因此明确检查失败。该结果没有证明整体资源节省，未生成检测器、完整工程或板端帧率。不能把单元算术测试通过描述成检测器优化成功。

未实现 HLS RTL blackbox 集成。相关接口调研参考[AMD文档](https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/JSON-File-for-RTL-Blackbox)。后续实际候选转向相邻像素共享权重，见 `../spatial_pair_v190/`。
