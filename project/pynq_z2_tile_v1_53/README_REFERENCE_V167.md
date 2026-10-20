# TileLab：单片瓷砖良品参照检测项目

PYNQ-Z2 / xc7z020clg400-1，Vivado与Vitis 2025.2，Windows上位机。按花色保存完整良品参照，固定位置、固定光照，在完整500×500像素表面寻找变化候选。未训练新模型。

本项目是电脑与FPGA协同的竞赛原型：电脑负责配准、光照估计和区域分析；FPGA完成整幅Q8归一化、亮度/色度差分及强弱标志；ARM负责DDR和网络。输入视频720p60，不等于每秒完成60次独立检测。实际资源、耗时、失败与适用边界见随包技术报告和evidence中的原始记录。

程序生成用例、HDMI回放和真实实体瓷砖准确率分开记录。低对比度单像素线仍有漏检；部分正常输入仍可能因质量条件不满足而拒判。拒判与未报警都不是良品认证。当前没有实体瓷砖相机成像的独立准确率验收记录，不能承诺国奖。

## 目录

发布包中的`project`是源工程：`experimental/reference_v167`为HLS与固件服务；`rtl`、`ip_repo`和`constraints`为视频采集模板；`scripts/reference_v167`生成独立的新硬件工程；`pynq_z2_tile_v1_53.sdk/ethernet_sources`是编译种子；`host`为工作站；`tools/reference_tile`为冻结算法依赖和可执行参考；`releases/v167`为匹配BIT/XSA/ELF。保留模板路径是为了构建脚本直接运行，不能据旧目录名判断当前版本。

`evidence`保存本版本的技术报告、测试汇总、实板记录及演示；`demo_player`是独立HDMI图像源；`project/skill`提供通用数组和部署校验工具。旧比赛报告与历史版本不混入此发布包。

## 安装与运行

安装Python 3.12、NumPy、Pillow，以及Vivado/Vitis 2025.2和JTAG驱动。报告重建还需要ReportLab。将电脑HDMI输出连接开发板HDMI IN，接好网线和USB JTAG。视频输出必须为1280×720、60 Hz，开发板作为扩展屏；瓷砖完整表面应落在[390,110]至[889,609]的固定暗背景视野内。

```powershell
python -m pip install numpy pillow
.\start.ps1 -Python python -Board 192.168.33.10 -Program -Xsdb D:/2025.2/Vitis/bin/xsdb.bat
```

`-Program`执行易失性JTAG下载，不写Flash。下载前关闭已有工作站和HDMI演示窗口。电脑有线IP须与板卡直连地址同网段；例如本次实测电脑192.168.33.30、板卡192.168.33.10。下载脚本核验文件哈希、时序、XSA内嵌BIT及板端启动身份。

打开`http://127.0.0.1:8771`。填写花色编号，确认当前完整良品后保存参照；随后放入同花色被测瓷砖并检测。所有图像与结果存入`project/host/runtime/reference_v167`，标定版本不可覆盖。更换算法后旧标定会拒绝使用。

无需手动编辑播放器命令的一键演示：在上述启动命令增加`-Demo`，网页会提供六类表面的良品、人工细线和拒判演示按钮，并明确标注合成回放。`-Demo`会启动第二屏播放器；开始前关闭其他占用同一第二屏的演示窗口。

若开发板已运行对应镜像，可不带`-Program`启动。也可直接执行`python project/host/reference_station.py --ethernet 192.168.33.10`。未连接匹配开发板时不会静默改用电脑检测结果。

## 可复现的HDMI演示

先在扩展屏配置完成后启动独立播放器：

```powershell
powershell -ExecutionPolicy Bypass -File demo_player/host/hdmi_display.ps1 -Root (Resolve-Path demo_player).Path
```

演示窗口只应出现在开发板对应的第二屏。`demo_player/host/display_command.txt`可写入`ref_000`至`ref_023`选择图像；每组四张依次为良品参照、正常扰动、人工细线和位姿超限。标注与图像哈希见manifest。它们是程序生成测试图，经实际HDMI进入开发板，不是相机拍摄的真实裂纹。

自动回放脚本`replay_board.py`需要播放器根目录、独立新输出目录及本次下载的proof.json。它对所有硬件差异像素运行独立参考，保存后才确认采集事件。`board_faults.py`另外测试损坏请求、截断和断线后的恢复。

## 从源代码重新构建

所有输出均使用不存在的新目录，原有发布文件不会被覆盖。在`project`目录操作，下面的输出位置仅是示例：

```powershell
$env:TILE_HLS_OUT='D:/tilelab_build/hls01'
vitis-run.bat --mode hls --tcl scripts/reference_v167/build_hls.tcl
python scripts/reference_v167/prepare_video_build.py --hls D:/tilelab_build/hls01 --out D:/tilelab_build/video01
```

进入`video01`，运行`vivado.bat -mode batch -source scripts/build_single_tile.tcl`。它检查建立/保持时间和DRC，导出匹配BIT/XSA。硬件位于`video01/reports/v164/hardware_run01`，此路径名仅用于构建兼容，不代表旧V164检测器。

回到源工程，设置`TILE_REF_WORKSPACE`为新建的绝对`.sdk`目录，`TILE_REF_HARDWARE`为上述硬件输出目录，`TILE_REF_HLS`为HLS目录，然后执行`vitis.bat -s scripts/reference_v167/build_software.py`。该脚本生成新的PS平台与固件，TCP接收窗口为65535字节。默认完整重建，不依赖本机既有平台。

最后用`seal_and_program.py --hardware ... --software ... --hls ... --out ...`封存；该步骤默认不下载。使用`program_release.py --bundle ... --xsdb ... --out ...`进行明确的易失性下载。完整参数见各脚本`--help`。

## 验证与提交

在`project/host`运行`python -m unittest test_reference_v167 -v`。C服务测试需要GCC：`python project/scripts/reference_v167/test_service.py --compiler gcc --out new_test_directory`。HLS构建包括C仿真与完整图RTL联合仿真，不能跳过失败后继续生成发布版。

`PACKAGE_MANIFEST.json`列出发布文件哈希；部署清单另外绑定BIT、XSA、ELF、源代码和时序报告。技术报告逐项列明已通过及未通过内容。正式报名信息、赛事模板与实体准确率验收仍须按参赛队和赛事实际要求核对，工程脚本不代替这些手续。
