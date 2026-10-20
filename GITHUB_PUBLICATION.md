# GitHub 版本说明

仓库：https://github.com/fangdut/TileLab-PYNQ-Z2

本次工程候选保存在 `single-tile-v164` 分支；`main` 保留原V1.53.1历史版本。分支包含单片配置、当前源代码、工作站、离线复现、匹配的BIT/XSA/ELF及本次构建和回归证据。

**彩绘／多材质准确率未通过验收，也没有V164本次实板验收。** 当前项目入口、失败样本和限制见根目录README及项目`reports/v164`。不要把历史提交文档或旧固件视为本次通过证明。

原发布记录与原文件清单保存在 `project/pynq_z2_tile_v1_53/reports/history/v153_entrypoints/`。当前文件清单不包含自身，上传成功以实际Git远端提交核验为准。

V165参照原型另存于 `single-tile-reference-v165` 分支，基于V164快照继续开发；新参照算法尚未部署上板，V164分支仍保留原快照。当前参照验证与限制见 `reports/v165/STATUS.json`。

V166改进保存在 `single-tile-reference-v166` 分支：新增离线亮度／色度参照差分、拒判纳入验收、独立窗口算术RTL与实板自检、V164检测器的50张实际HDMI回放及无外接显示器热插拔修正。当前状态见 `reports/v166/STATUS.json`。完整参照视频算法和独立目标材料准确率仍未验收；不以算术核上板替代整机参照检测验收。原V164部署产物保留，新的传输与自检镜像分别存放。
