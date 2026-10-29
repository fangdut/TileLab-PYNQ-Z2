# V202工程包复现与结果比对

报告V205仅修订材料，复现对象仍为V202工程。以下命令是操作说明，本次材料修订没有执行部署、编译、上板或重新验收。

## 1 获得并校验工程包

使用随附`TileLab_Engineering_V202_20261027.zip`，SHA256应为`23631c497e94325312e9f2df77ac4a551cdede7e4d21eb584cdbc9c9f3a06e54`。当前已交付的本地包位于工程根目录`engineering_delivery_20261027/`；GitHub并未发布这个完整ZIP为下载资产，仓库中的LOCAL_ARCHIVE.json只是清单，不是下载链接。

在ZIP所在目录执行：

```powershell
$archive = Resolve-Path -LiteralPath '.\TileLab_Engineering_V202_20261027.zip'
(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
Expand-Archive -LiteralPath $archive -DestinationPath '.\TileLab_V202_replay'
```

进入解压后包含`start_station.ps1`、`profiles/`、`verified_hdmi/`和`project/`的工程包根目录。使用新目录；若解压工具额外生成一层文件夹，以实际根目录为准。

## 2 连接并准备环境

按[接线说明](hardware_setup.md)连接供电、USB JTAG和Ethernet。电脑网口例如192.168.33.1/24，板端192.168.33.10。安装Vivado/Vitis 2025.2、USB驱动、Python 3.12；在实际解释器环境执行：

```powershell
python -m pip install -r .\requirements.txt
$env:TILELAB_PYTHON = (Get-Command python).Source
# XSDB安装位置不同时，设置实际路径，例如：
# $env:TILELAB_XSDB = 'D:\2025.2\Vitis\bin\xsdb.bat'
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_station.ps1 -VerifyOnly
```

`-VerifyOnly`检查文件和BIT/XSA/ELF/模型配对，不开始下载。通过后确认没有别的工作站或HDMI程序控制同一开发板，再启动：

```powershell
& '.\启动检测.cmd'
```

脚本会易失下载、上传已封存参照并打开`http://127.0.0.1:8793/`，不写Flash。不要假定旧服务或开发板仍在线。

## 3 核验参照并检测

1. 选择纹理砖参照，填写操作员、材质和真实条件“公开照片回放”。没有相机的演示不填写现场光照标定。
2. 使用至少3张不同良品和1张已知缺陷，逐张载入固定输入、PL检测、记录复核、确认处置；全部一致后封存本批资格。不要重复同图凑数量。
3. 正式检测重复载入、固定、PL检测、复核、确认逻辑放行或隔离。原图宽高均不超过1024，不使用PC缩放/推理后备。
4. 导出CSV与JSON。复核冲突、启动身份变化、源图或参照变化会使旧资格/结果不可继续放行；保留失败记录并重新核验。

包内照片目录`project/data/stop_inspect_demo/`及闭环目录由catalog标明。若需补齐公共回放原图，可在包根目录查看并运行`python project/tools/fetch_closed_loop_demo.py --help`，按其catalog与V199输入清单下载和核对SHA256。陶瓦衍生720方图属于披露的离线数据准备。

## 4 核对证据

界面显示的单张结果不等于117图统计。基准数据为[summary.json](../project/pynq_z2_tile_v1_53/reports/v202/summary.json)；[metrics.csv](../metrics/metrics.csv)保留逐项JSON来源，`metrics/scripts/summarize_v202.py`可离线重建汇总。

- 对每张输入核对SHA256、模型、尺寸；比较28×28分数、原图掩膜和元数据，帧序号因重跑变化不要求等于存档。
- 冻结117张公开开发图：33张正常不报警、84张缺陷报警；这不是独立精度。仅演示若干张不能声称复现全部117图。
- PL均时124.71544ms；传图加检测501.79149ms，不包含解码、完整UI复核和保存。复测速度受环境影响，不应把单次耗时强制等同均值。
- 100逻辑周期均时1.219721s包含0.25s脚本复核等待、API与落盘。脚本按已知标签复核，不是人工/机械产能。

`reports/v202/run_retest_record.py`是保留本机路径的历史运行记录，不能直接当作跨机器一键验收入口。若要重跑整套117图和100周期，须先适配新runtime、输入清单及输出目录，再按冻结plan核对；此材料修订未验证这一跨机器自动化过程。原始证据复算与重新上板验收是两件事。

完成当前工件后运行包内`停止工作站.cmd`，保留runtime记录。

## 5 仅从GitHub源码开始时

```powershell
git clone --branch fpga-real-texture-v170 https://github.com/fangdut/TileLab-PYNQ-Z2.git
Set-Location .\TileLab-PYNQ-Z2
python .\metrics\scripts\summarize_v202.py --out .\runtime_metrics.csv
```

此步骤只克隆源码并复算已存档指标，不访问板卡。仓库包含可重建历史V179运行包的`tools/package_stop_station.py`、V200固件源码及构建记录，但默认旧打包命令不会自动生成已验收V202双参照闭环包。V200重建还需要匹配BSP、两个参照和单独验证的传输固件工作区；其说明见[transport_v200](../project/pynq_z2_tile_v1_53/experimental/transport_v200/README.md)。本次没有完成或声称“任意新机器仅clone即可一键复现整套V202”。

复现交付时应同时提供V202完整工程ZIP、V205报告、仓库分支链接。源代码保留在原目录，避免为了推荐目录样式移动构建路径。
