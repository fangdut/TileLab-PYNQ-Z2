# 工程恢复与构建入口

工程文件以engineering/中的纯英文路径提交。build/file_map.json记录每个文件的原始相对路径、字节数与SHA256。仅对包内路径规范化，文件内容保持原已验证字节，避免破坏厂商Makefile、CMakeLists.txt及脚本大小写依赖。

`python build/restore_engineering.py --out ../tilelab_runtime` 在新目录重建匹配的独立工程，并验证全部源文件。目标目录必须为空，不访问板卡、不写Flash。再运行 `powershell -NoProfile -ExecutionPolicy Bypass -File ../tilelab_runtime/start_station.ps1 -VerifyOnly` 做配对、时钟、复位及时序检查。

恢复不等于重新综合。完整源码构建入口位于恢复目录verified_hdmi/source/scripts/texture_v170/build_candidate.py、build_hardware.tcl与build_software.py；接受的HLS源码为verified_hdmi/source/texture_integer.cpp，HLS导出为verified_hdmi/hls/accepted_export.zip。此次另补入硬件Tcl实际依赖的本地ip_repo、constraints与缺失辅助脚本，来源commit 43e52652bc7e9ef6cfa4aadf5b1bdbeb8654c4a2。清单逐文件记录来源。

需要用户自行安装AMD Vivado/Vitis2025.2及板卡驱动。重建HLS、布局布线与固件耗时较长，本次包结构修订只完成静态依赖核查、字节恢复和离线保护测试，没有重新综合或重新上板；原BIT/XSA/ELF/模型保持冻结值。后续重新综合的产物须重新验证后才能替换冻结版本。
