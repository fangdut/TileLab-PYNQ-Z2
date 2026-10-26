# 第三方来源与数据范围

开发工具为AMD Vivado/Vitis 2025.2；HLS导出驱动、PS初始化与Xilinx BSP保留其源文件版权和许可声明。发布包不是对这些第三方代码的重新授权。使用工具及器件IP须遵守对应AMD许可。

`ip_repo`中的Digilent HDMI IP保留BSD 3-Clause许可及源文件中的版权、再分发条件和免责声明。

运行依赖为Python、NumPy和Pillow，报告生成依赖ReportLab；依赖通过各自发行渠道安装，未把Python运行环境作为本项目原创代码发布。演示视频由FFmpeg编码，FFmpeg可执行文件不随工程包分发。

本版本实板演示与新增算法图由项目脚本程序生成，并明确标注人工细线，不是网络真实裂纹。旧阶段数据来源和许可见仓库历史DATA_PROVENANCE_V164.md；未将许可未澄清的照片混入本版本发布包。

项目所有者已于2026-10-20授权原创TileLab代码与文档采用MIT许可。根目录LICENSE为正式许可文本，LICENSE_SCOPE.md说明适用范围；第三方代码、数据、模板与工具保持其原有声明，不改授MIT许可。

V168新增实拍模式：MVTec AD照片、标注与派生正常特征库保留CC BY-NC-SA 4.0，来源https://www.mvtec.com/research-teaching/datasets/mvtec-ad，引用Bergmann et al., CVPR 2019；Voxel51镜像固定版本记录于逐图清单。图片及特征库不在MIT授权范围。本轮实拍开发结果与V167程序生成图板测分开保存。

V168使用PyTorch和TorchVision（各自保留上游许可），ImageNet预训练WideResNet50-2权重来自https://download.pytorch.org/models/wide_resnet50_2-95faca4d.pth；保留官方来源、SHA256和上游条款，不改授MIT。Git不包含该大权重文件，启动前由校验下载脚本取得。方法参考Roth et al., Towards Total Recall in Industrial Anomaly Detection, CVPR 2022；本工程是简化实现，不等同论文原模型或论文结果。


## V197 HFENet source

RobotvisionLab, Copyright2021, MIT. Pinned source6edf57293da051a5d9d2164482f88b68ef45c11f; original module and license preserved under project/pynq_z2_tile_v1_53/experimental/hfenet_v197/vendor. Published epoch69 selected before evaluation, no new training. Checkpoint and data-derived binaries remain local; author photographs/labels are not redistributed under the software license. Author-model evaluation on author validation data is not independent validation.
