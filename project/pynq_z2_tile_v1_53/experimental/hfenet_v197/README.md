# HFENet整数硬件迁移实验

使用RobotvisionLab公开的HFENet预训练epoch69，没有新训练。作者固定版本：
https://github.com/RobotvisionLab/HFENet/tree/6edf57293da051a5d9d2164482f88b68ef45c11f

`vendor/hfenet.py`是保留原样的作者网络定义，其版权和MIT许可在vendor/LICENSE。
不要导入作者main.py，它在导入时初始化CUDA和训练对象。本实验只导入网络类。
权重仅按固定来源下载到本地，Git中不分发权重、照片、标注或预测栅格。
软件MIT不能自动作为独立照片数据的再分发许可。作者模型不是本项目原创模型。

## 已验证与未完成

原始灰度扫描条带256×1408，不是完整实体瓷砖照片。作者模型在作者数据上的
80文件复现：浮点和16位整数参考均40/40缺陷检出、0/40良品误报；可能有作者
模型选择与验证集重叠，不是独立盲测。数字边界误差见reports/v197/status.html。

完整网络目前只有离线整数参考，尚无完整新检测器BIT、整机RTL、实板或FPS。
运行工作站仍使用原100MHz稳定版。禁止用离线CPU测试充当FPGA结果。

`norm_integer.cpp`实现独立InstanceNorm实验单元，mode2从DDR数据计算矩，
用整数平方根和按通道生成的定点仿射系数做第二遍归一化。它不是完整检测器。
`preprocess_integer.cpp`实现独立灰度直方图均衡与饱和叠加，限定已研究的灰度
输入；颜色不一致返回5，非法几何返回4。两者实际C/RTL进展以报告为准。

## 整数参考约定

- 权重／中间数据16位，按正常标定范围选择2的幂尺度，固定2倍裕量。
- 卷积按整数MAC计算。离线Float64操作数都是整数，累计界限低于2^53，因此
  该工具计算整数MAC的精确审计结果；实际硬件必须使用整数DSP累加并再验证。
- InstanceNorm逐输入统计，不能折成固定BatchNorm：N为像素数、S为和、Q为
  平方和、s为输入尺度，V=NQ−S²+round(epsilon*N²/s²)。
- 计算floor(sqrt(V))；gamma/beta用Q30，逐通道生成Q36系数，逐像素乘加、
  最近偶数舍入并截到int16。误差通过整个网络验证，不宣称与浮点逐像素相同。
- 残差和拼接用移位对齐；双线性2倍插值按align_corners=False的1/4、3/4
  权重和复制边界实现。最终sigmoid>0.5替换成整数logit>0。
- 当前预处理的整数有理数舍入在144张完整原图中与作者OpenCV处理逐字节一致；
  不把有限样本的符合性扩大成所有直方图上通用的浮点等价证明。

## 复现入口

research/保留本机路径下的冻结协议、离线标定和验证脚本；不由工作站导入。
依赖现有Torch/NumPy/Pillow；OpenCV仅用于作者离线对照，隔离安装4.10.0.84。

```text
python experimental/hfenet_v197/test_integer_geometry.py
python experimental/hfenet_v197/make_norm_vectors.py --out NEW_VECTORS
TILE_NORM_HLS=NEW_HLS; TILE_NORM_VECTORS=NEW_VECTORS
vitis-run --mode hls --tcl experimental/hfenet_v197/build_norm.tcl
```

上述环境变量示意须按Windows PowerShell语法设置。归一化co-sim测试台为完整AXI
深度分配内存；不能用短逻辑fixture的数组指针冒充完整接口，否则wrapper先越界。
合成fixture仅证明整数运算，不计为实拍准确率数据。

下一阶段需要完整共享卷积引擎、DDR调度和源绑定的整机验证；原1024单边图像
传输限制还不支持1408行，需由新硬件和固件契约一起修改，不能偷偷缩放。
保留停驻检测与人工确认，暂不承诺10FPS。
