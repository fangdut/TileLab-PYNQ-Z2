# 多算子低延迟工业视觉检测系统

基于FPGA的瓷砖表面缺陷筛查系统，工程代号TileLab。该RAR为自主选题初级组提交物三合一：完整工程文件、可复用技能包、设计报告及大模型协作记录。提交整理版V209，视觉计算核心仍为冻结V202，流水线应用为V208。输入为真实照片，输送为电脑模拟。

## 快速检查与复现

1. Python3.10及以上，安装NumPy/Pillow，安装AMD2025.2工具与驱动（板卡运行时需要）。
2. `python build/restore_engineering.py --out ../tilelab_runtime`。工程恢复只校验并复制文件，不访问板卡。
3. `powershell -NoProfile -ExecutionPolicy Bypass -File ../tilelab_runtime/start_station.ps1 -VerifyOnly`。
4. 按board/README.md接线，在恢复目录执行start_conveyor.ps1，完成8793工位核验后使用8794流水线。
5. `python skill/run_reuse_checks.py --out ../skill_check.json --bundle ../tilelab_runtime` 验证通用校验技能。

## 三类提交内容与目录对照

|指南目录/要求|本包位置|
|---|---|
|src/完整RTL、HLS、PS与PC源码|engineering/project/host/、engineering/verified_hdmi/source/；build/file_map.json可还原全部原始文件名|
|sim/仿真、验证脚本及结果|sim/README.md导航至engineering/project/reports/与HLS/RTL测试台|
|build/构建脚本、综合实现报告|build/及engineering/verified_hdmi/hardware/的timing_summary.rpt、utilization.rpt、drc.rpt等|
|board/上板工程、脚本及实测输出|board/README.md、恢复后的匹配BIT/XSA/ELF与project/reports/|
|data/测试数据与参考结果|data/README.md、engineering/profiles/、project/data/、verified_hdmi/evidence/|
|skill/技能包|顶层skill/，含3个通用校验工具、复用测试、适用范围、失败来源和失效条件|
|report/设计报告与协作记录|顶层report/design_report.docx、design_report.pdf、llm_collaboration.md及性能对照|

## 命名与字节保真

提交目录和文件使用英文ASCII路径，普通名称小写；按指南示例保留README.md约定。工程原始文件名（含厂商要求的大小写和历史中文文档名）只出现在file_map.json正文。恢复工具在指定的包外运行目录重建原始布局，保证原部署脚本和哈希不因重命名失效。目录对照属于指南允许的替代组织方式，未把推荐树误作强制结构。

manifest.json核对三合一包；build/file_map.json核对工程源文件；恢复后的原manifest核对冻结工程。它们证明一致性，不证明来源可信或跨设备成功。此次修订没有新增上板或跨板PYNQ验证。

## 证据与许可

报告给出同口径32图传输优化前后对照，PL资源不变；117图是开发集，脚本复核不是本人复核。技能复用采用新临时目录、DSP数组/通信文件及合成部署夹具，并另核对真实XSA/BIT配对，具体结果见skill/verification.json。

原创代码MIT，数据、模型和厂商内容保留各自许可。大模型记录为真实节选及明确标注的历史摘要，没有补写不存在的回答。完整历史聊天未全部导出。PYNQ-Z2板卡不等于PYNQ Python框架，此包不声称已完成Overlay/DMA通用技能的跨板验证。
