# 比赛模板技术报告

报告为 V1.53.1 的比赛模板版，共 16 页。保留用户提供模板的五部分结构、字体、比赛页眉和页码；内容含系统框图、FPGA 算法公式、Vitis 与电脑分工、真实验收结果及局限。

## 阅读

- `TileLab_比赛技术报告_模板版.docx` 是可编辑报告。
- 项目 `docs` 中的 67 页教学手册与 18 页视频拍摄方案保持原样。
- `assets` 保存报告使用的系统图与同帧 PL 证据可视化；来源见 `assets/evidence_sources.json`。
- 网页截图来自实际复核界面，接收暂停提示未作修改。它不代表截图时正在采集。
- 完整接线的正面和 45° 实物照片仍须实拍；没有虚构相机、外壳或输送带。

## 生成与验证

`tools/build_report.py` 使用 lxml 和 Pillow 对原模板进行 OOXML 包修补。运行时通过 `--reference` 提供比赛原始模板，其 SHA-256 必须为 `d15a2aa186f600cb9c234bffd9deff0c4e9b05c569643d8a81d536f66f424f0c`；可用 `--project` 和 `--output` 指定路径。原始模板没有另行作为项目素材公开。

```powershell
python tools/build_report.py --reference <比赛原模板.docx>
```

源字体使用 Windows 宋体、Times New Roman 和微软雅黑。报告已由 Microsoft Word 只读导出，并使用文档渲染工具逐页检查；QA 摘要见 `document_qa.json`。没有改变冻结工程、硬件比特流、ELF 或原验收记录。
