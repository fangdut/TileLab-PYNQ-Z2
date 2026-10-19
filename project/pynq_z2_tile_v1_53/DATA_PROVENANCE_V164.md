# V1.64 数据与证据说明

本分支在既有公开仓库基础上保存工程，没有新增 HFENet 原始图片包。第三方代码、IP 与照片继续遵循 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 中各自的许可；本分支未对第三方内容重新授予许可证。

当前50图回归使用仓库原有的 MVTec AD tile 照片与裂纹掩码：17张 crack、33张 good。来源、原始ID、相对路径与引用记录在 `data/real_tiles/manifest.json`，HDMI画布映射在 `data/real_tiles/hdmi_manifest.json`。资料标注许可为 CC BY-NC-SA 4.0，来源为 [MVTec AD 官方数据集](https://www.mvtec.com/research-teaching/datasets/mvtec-ad)，引用 Bergmann et al., CVPR 2019 / IJCV 2021。商业用途应遵循原数据集条款。

两组回归区别必须保留：

1. `historical_acquired`：原有 `validation/reference_rgb/real_NNN_original.png`，是此前 HDMI 成像链路采集并解码的 RGB 图。
2. `stimulus`：原有 `data/real_tiles/hdmi/real_NNN.png`，是送入 HDMI 的照片画布，尚未经过那条实采链路。

它们来自同一批源图，不能当作两组独立样本，也不能合并为100张。V164没有重新拍摄或重新上板采集。这里只在电脑上将已有照片输入当前固定ROI参考程序。

原始历史 manifest 中保留的 `alarm`、`pixel_tp` 等字段是旧算法记录；V164评估只从中读取ID、类别和路径，重新计算当前掩码、框、精确率与召回率，不复用旧分数。历史 manifest 中关于“测试图未参与阈值选择”的早期说明不适用于后续反复开发：现在这些图均是已暴露开发数据。

`models/oof_v159/manifest.json` 明确记录源图ID到折的映射、折模型SHA256和开发集选择限制。相同源图的另一种输入呈现仍沿用原图所在折，不把它误计为新盲测。模型为历史冻结产物，本次不训练新模型。折模型仅供开发回归；部署使用冻结全量拟合模型，其训练重放分数不能当独立准确率。

数据包中还保留油污、胶条等历史研究照片，它们没有被冒充裂纹或正常样本混入本次50图统计。网页当前只开放17张裂纹、33张正常以及空视野的测试输入。

彩绘、砖缝、多材质研究的历史失败结论保留在开发记录中，但当前没有足够且独立的单片彩绘／多材质测试集。不能把人工P图或生成裂纹作为真实裂纹准确率依据。后续如添加合成样本，必须单列“合成”，并按原始完整砖图分组，避免原图或增强变体跨训练／测试泄漏。
