# GitHub 发布状态

项目已上传到公开仓库：[https://github.com/fangdut/TileLab-PYNQ-Z2](https://github.com/fangdut/TileLab-PYNQ-Z2)，默认分支 `main`。

首轮推送经 GitHub API 与匿名 Git 读取核验：远端与本地提交 `ec120a3eccc7ea5bf8fb605d8a5c45bfb486cc3e` 一致，6478 个文件的 Git blob 标识与文件模式逐一匹配，远端目录没有截断。共享代理的匿名 API 达到速率上限，因此元数据核验使用已授权账号；另独立关闭凭据辅助器，确认无需登录即可读取公开分支。最终发布元数据补充后再次核验，独立核验记录保存在本地提交交付目录。

仓库包含 RTL、IP、约束、Vivado XPR/BD、Vitis `.sdk` 工作区及源代码与构建产物、电脑工作站、播放器、测试脚本和测试结果、照片来源与许可、PDF 手册、视频拍摄方案，以及 16 页比赛模板 Word 技术报告和报告生成源码。没有上传登录凭据、运行数据库、临时文件或持续采集截图。

FPGA 负责裂纹候选检测、区域框和产品最佳帧选择；Vitis 负责 DMA 采集、缓存、控制和 TCP 传输；电脑负责证据保存与人工复核。当前是已校准材料的工程原型，未验证真实工业相机与产线，跨材质漏检仍需改进。

```powershell
git clone https://github.com/fangdut/TileLab-PYNQ-Z2.git
```

进入 `project/pynq_z2_tile_v1_53` 查看工程 README；`.sdk` 文件夹为 Vitis workspace。原始完整 ZIP 与精简源码 ZIP 已保留，源码阅读包省略工程照片，不能单独复现全部照片测试。第三方代码与照片继续遵循各自许可，详见项目 `THIRD_PARTY_NOTICES.md`；公开上传不构成重新授予第三方素材许可证。
