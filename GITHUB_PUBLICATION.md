# GitHub 发布状态

当前已准备完整可发布本地 Git 仓库，包含 RTL、IP、约束、Vivado XPR/BD、Vitis .sdk 工作区及源码、电脑端代码、照片来源与许可、测试脚本与结果、PDF 与 PDF 生成源码。未包含账号凭据、运行数据库和自动留图。

尚未连接 GitHub 账号，因此尚无远端仓库链接。不得将本地提交或预计仓库名当作已经上传。连接 GitHub 后可创建 TileLab-PYNQ-Z2 仓库并推送本地已审查提交；实际成功后检查远端默认分支及文件，再记录真实链接。

如自行使用已登录 GitHub CLI，从本目录运行：

```powershell
gh repo create TileLab-PYNQ-Z2 --public --source . --remote origin --push
gh repo view --json url
```

这些命令要求 gh 已安装并登录，当前电脑没有该条件。公开仅授权的项目内容；第三方照片仍遵循各自许可，详细见工程 THIRD_PARTY_NOTICES.md。完整 ZIP 为可复现包；源码 ZIP 不含照片，不能单独运行全部演示。
