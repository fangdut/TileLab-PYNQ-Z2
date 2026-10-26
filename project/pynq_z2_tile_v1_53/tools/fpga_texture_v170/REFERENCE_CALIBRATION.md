# 良品参照标定：离线设计与 FPGA 部署

`fit_reference_bank.py` 是离线工具，不能导入工作站的运行时检测路径。
它沿用基线量化 CNN、激活范围、128→64维投影及输入整数运算，
仅用良品生成1024个参照中心，并以另组良品的最大评分加1冻结阈值。
测试缺陷的标签和评分不参与参照或阈值选择。

本轮数据为作者发布的真实陶瓦照片，不是地砖或彩绘材质的验收集。
训练、标定、测试的原图文件哈希互斥，但无法证明实体工件独立。
先后两轮测试互斥；第一轮失败结果保留。整图离线缩为720×720是明确披露的
输入准备操作，不能称作原始高分辨率无损测试，也不能与桌面HDMI缩放当成逐像素相同。

## 重建

从仓库 `project/pynq_z2_tile_v1_53` 目录运行（用实际路径替换占位符）：

```text
python tools/fetch_reference_v195.py --evidence reports/v195/r2/source --out NEW_DATASET
python tools/fpga_texture_v170/fit_reference_bank.py --base ACCEPTED_PROFILE --dataset NEW_DATASET --out NEW_PROFILE
```

Python/Pillow版本见报告环境记录。PNG编码不一致时下载工具会拒绝匹配声明。
本轮报告的 `reference_artifacts.zip` 含 `base_profile`、两组候选及匹配固件，
其中的冻结量化图可用于离线复现；稳定BIT/XSA仍由已验证V179运行包提供。
不要用不匹配的模型替代。
模型二进制只允许阈值字段和参照区变化，导出器还会检查整数累加/量化范围。

## 部署约束

传输固件编译时绑定模型CRC及大小，不能只在旧固件下换文件或伪造CRC。
用 `scripts/texture_v170/build_software.py`，将 `TILE_TEXTURE_MODEL` 指向新配置、
`TILE_TEXTURE_SW` 指向全新工作区，保留实际BIT/XSA及HLS路径。
然后用 `program_board.py` 易失下载，记录真实BIT/XSA/ELF/模型SHA及启动编号。
评分、掩膜、阈值比较、图像报警在PL；PC和ARM只传输及管理流程。
离线整数参考用于核对，不是运行时的检测后备。

本轮候选不自动获得工作站放行资格，不能把小样本结果升级为任意材质准确率。
稳定演示配置与候选实验分开保存；失败候选不能覆盖已验证包。
完整HDMI候选验收仍需另外测量真实采集帧、颜色校正及双ARM停止运行。

## 许可

来源照片、报告缩略图：`ceramics-defects-detection`，
DOI10.17632/47x6jdbr5j.1，CC BY4.0；作者为 Lucileide Aquino do Nascimento、
Otilio Paulo、Gilvan Moreira da Paz、Micherlane Rodrigues Machado da Silva。
缩略图经过缩放和文字标注。继承的基线投影来自MVTec开发标定，模型仍保留
原有非商业及共享限制，不因这次更换参照中心而成为MIT材料。原创工具代码适用项目MIT。
