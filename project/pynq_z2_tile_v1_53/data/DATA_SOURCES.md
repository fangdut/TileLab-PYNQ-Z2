# 当前发布包的照片来源与处理

## MVTec AD / tile

来源：https://www.mvtec.com/research-teaching/datasets/mvtec-ad ，Bergmann 等，CVPR 2019 / IJCV 2021。原始类别包含 347 张照片；原始路径与 ID 见 `real_tiles/manifest.json`，镜像来源记录在同一文件。许可 **CC BY-NC-SA 4.0**，完整文本 `real_tiles/license.txt`。

本包提供 117 张测试照片的 HDMI 场景、230 张正常标定照片的 HDMI 场景、运动用的预加载照片和裂纹真值掩码。照片缩放、嵌入合成传送带背景、添加身份帧码属于衍生处理；衍生照片继续按 CC BY-NC-SA 4.0 提供。身份帧码只用于工程测试，输入中没有提前画检测红框。

`validation/reference_rgb` 与 `reports/v153/real_board*` 的实际 HDMI 采集照片同样继承该许可。历史 17 张裂纹 + 33 张正常样本反复用于开发回归，不是新工厂独立产品集。当前计算所使用的实际 HDMI RGB 可能与源文件颜色不同，应固定显卡/显示设置后重新标定。

## MCS2 / RGB 大理石裂纹

来源：https://github.com/MachineLearningVisionRG/mcs2-dataset ，Vrochidou 等，2023；DOI 10.1109/AIIoT58121.2023.10174288。许可 **CC BY 4.0**，完整文本 `independent_mcs2/LICENSE.txt`。

本包包含 24 张 RGB 原图和标签、500×500 缩放 HDMI 场景、标签缩放和前 4 张照片的运动用素材。原图下载、单文件哈希、种子、配方与处理方式见 `independent_mcs2/manifest.json`。这些都是有裂纹的大理石图；没有正常整砖，不能据此计算图像级误报率。固定配方第一次实板检测仅 1/24 报警；后续阈值探索已属于开发实验，不可再称盲测。

## 程序与 AI 合成输入

`synthetic`、`conveyor`、`dark_gate` 用于运动、门禁、噪声、传输和边界工程验证。随机种子及早期 AI 外观素材说明见 `GENERATION_PROVENANCE.md` 与各 manifest。它们不是独立真实缺陷产品，不应和真实样本混在一起计算工业检出率。

## 没有随包发布的历史研究数据

Mendeley 屋面陶瓦与 Ceramic Cracks 曾用于旧版本的离线研究。当前包不含它们的原始集合或派生预览；没有明确许可的 Ceramic Cracks 不作公开再分发。历史摘要若提及这些研究，只能按其历史范围理解，不能描述成当前新实板验收。
