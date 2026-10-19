# V1.65：按花色良品参照原型

使用者已确认允许“每种花色保存良品参照，固定拍摄位置和光照”。本分支实现离线标定、对齐、光照补偿、变化检测及独立的整数差分RTL。**尚未接入完整FPGA工程，现有BIT/XSA/ELF仍是V164；没有新分类模型训练，没有本次实板或真实彩绘裂纹准确率验收。**

## 做了什么

标定包绑定具体花色ID、完整原生720p良品图、500×500完整检测ROI、容差图、参数和代码SHA256。标定目录不可覆盖；换参照、换实现或改参数必须产生新版本。程序不会自动证明输入参照是良品，需由采集者确认。

对齐先搜索整数位移，再细化到1/16像素。参照已有的特征和完整边界剖面用于定位，避免新增缺陷主导位移评分；四个局部区域再检查是否符合平移假设。匹配双线性重采样传递，降低对齐插值在原有花纹边缘造成的假差异。该模型只是采样近似，没有真实相机光学验证。

每个颜色通道估计全局增益和偏置，用Q8整数补偿；纯色通道信息不足时只估计偏置。差分取三通道最大绝对残差，叠加参照边缘容差后形成强／弱候选，再检查区域像素、跨度与强种子。全部500×500像素参与检测，没有为减少误报缩边。

错花色ID、标定包变更、对齐不唯一、位移超限、局部几何不一致、异常曝光、饱和及大范围未解释变化均会停止判定。`REJECTED_INPUT` 的 `alarm` 为 `null`，不输出掩码，不代表正常。表面变化可能是裂纹、污渍、灰尘、釉面或印花变化，目前不做语义裂纹分类。

## 结果与限制

以下均不是独立真实准确率：

| 机制用例 | 数量 | 候选报警 | 拒判 | 无候选 |
|---|---:|---:|---:|---:|
| 程序构造正常图及采集扰动 | 36 | 2 | 1 | 33 |
| 人工细线 | 24 | 24 | 0 | 0 |
| 错参照、位移、旋转、曝光、遮挡压力 | 30 | 0 | 30 | 0 |
| 原仓库真实良品图与自身对照，只检查流程 | 33 | 0 | 0 | 33 |
| 不同真实良品跨实例压力，未确认花色及布局匹配 | 32 | 0 | 32 | 0 |

36个构造正常用例中，直接差分产生23次报警；当前参照原型为2次报警、1次拒判。剩余失败均来自6个JPEG扰动用例，其中2次误报、1次拒判。其他30个构造正常用例没有报警或拒判，但这个分项不能替代真实测试。24个人工细线均有真实人工GT交点的定位候选，不能称为真实裂纹检出率。

初版正常用例有6次报警、3次拒判，人工线条21/24触发定位；初版、阶段中间结果及对应源指纹均保留。高／低阈值18／9未改变。所有这些用例经过开发调试，不是盲测。

真实跨实例压力说明：**同材质类别不等于空间花纹匹配。** 一张随机石纹／木纹的良品图不能代表同类别所有砖。先验证同花色多块良品的正常变化；若布局或自然纹理变化很大，需要更多良品容差标定或其他方法。拒判率必须公开，不能当作零误报。

[图文报告](reports/v165/reference_report.html)、[全部逐用例结果](reports/v165/MECHANISM_FINAL.json)、[真实跨实例压力](reports/v165/CROSS_INSTANCE_STRESS.json)、[当前状态](reports/v165/STATUS.json)。真实同花色良品／裂纹配对数仍为0。两项真实诊断复用了同一批33张原图，不能称为65张独立真实样本。

## 离线标定与使用

需要Python3.12、NumPy、Pillow。参照和当前图必须来自相同成像链路、相同花色布局，保留完整1280×720输入和边界上下文；不要把网页商品图与相机采集图直接作逐像素对照。不自动缩放、裁去表面边缘或填补缺失图像。

在项目目录执行，每个花色使用独立标定目录：

```powershell
python -m pip install -r tools/reference_tile/requirements.txt
python tools/reference_tile/reference_tile.py calibrate --image captures/pattern_A_good.png --material-id pattern-A --out build_local/references/pattern_A_rev1
python tools/reference_tile/reference_tile.py inspect --bundle build_local/references/pattern_A_rev1 --material-id pattern-A --image captures/pattern_A_current.png --out build_local/inspection_001
```

输出`result.json`。成功比较时另有`aligned.png`、`mask.png`、`overlay.png`；质量拒判时退出码为3，只有拒判JSON。退出码0也不表示良品合格，需查看`alarm`与人工复核状态。改变代码后旧标定包会拒用，须重新标定。

只有仓库图时，可用`data/real_tiles/hdmi/real_035.png`进行标定，再与自身比较，检查安装与保存流程；这是自对照，不能验证真实准确率。

```powershell
python -m unittest discover -s tools/reference_tile -v
python tools/reference_tile/benchmark.py --out build_local/reference_mechanism
python tools/reference_tile/stress_cross_instance.py --out build_local/cross_instance_stress
python scripts/reference_v165/check_provenance.py
```

机制测试生成程序夹具及人工线条，不是相机照片。真实图片只使用仓库原有、来源明确的MVTec良品照片，不新增HFENet图片包，不把合成缺陷纳入真实裂纹分母。

## 实际新增的Verilog

`experimental/reference_v165/rtl/reference_difference_v165.v`是3级弹性流水线，输入必须是已经配对的普通RGB当前像素和参照像素，并同时携带增益、偏置、边缘容差、阈值、帧边带。其整数公式为：

```text
normalized = clip(((current * gain_q8 + 128) >> 8) + signed_offset, 0, 255)
score = max_channel(abs(reference - normalized))
strong = score > high + edge_tolerance
weak = score > low + (edge_tolerance >> 1)
```

8192组输入覆盖全部允许位宽、符号偏置、舍入、饱和、严格阈值、流水线空拍、背压、边带及传输中复位，逐项比对通过。独立综合约135 LUT、295寄存器、3 DSP、0 BRAM。OOC时钟偏斜估计有警告；**不作为完整系统时序、资源或帧率结论。**

```powershell
python scripts/reference_v165/prepare_difference_vectors.py --out build_local/reference_vectors
$env:TILE_REF_VECTORS=(Resolve-Path build_local/reference_vectors).Path
$env:TILE_REF_SIM_OUT='D:/TileBuild/ReferenceSim01'
& C:/AMD/2025.2/Vivado/bin/vivado.bat -mode batch -source scripts/reference_v165/test_difference.tcl
```

这份RTL没有接入V164的BD或运行工作站；在线工作站没有导入离线参照检测器，也不会把Python输出冒充PL结果。现有下载入口仍严格校验V164部署包。

## 下一段板端工作

完整参照RGB约750,000字节，容差图约250,000字节，共1,000,000字节；仅以每秒60次完整读取计算，约60MB/s，不含突发填充、协议、当前帧读写及网络开销。V164剩余BRAM约83KiB，不能直接存下整套参照。

需要接入DDR参照流和缓冲，绑定花色ID、参照版本、坐标、帧号与CRC，并保证在帧边界原子切换。必须检测参照欠流、错帧、旧参照和输入流丢失，出错不能输出正常判定。普通RGB与现有HDMI原生字节顺序需明确转换。原始HDMI不能任意停顿，不能直接依赖这个算术模块的背压来阻塞视频输入。

位移、光照系数与区域／拒判逻辑也要确定板端实现位置；当前离线对齐和区域分析没有被声称已实现于PL。下一步先补同花色多块良品和真实裂纹的配对证据，再完成参照数据通路及整机RTL、时序、资源和上板回归。
