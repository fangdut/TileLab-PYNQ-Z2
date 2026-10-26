# FPGA 输入区域候选

裁取固定标定区域的操作在PL、在归一化和CNN之前完成；电脑只发送完整输入和配置。
默认模型保留整图模式。它不自动找砖、不配准，也不保证砖体已完全进入检测框。
现场需要固定位置、光照，并把整片目标纳入标定区域；否则不能据局部结果放行整砖。

模型保留字20至26：`x,y,width,height,source_width,source_height,0x19600001`。
尺寸、边界或标记不匹配时硬件返回错误，不能静默裁剪或复用旧结果。
ROI评分网格对应局部输入，掩膜映射回完整源尺寸，框外为零。
结果头10至15回传六项区域参数；传输客户端检查它们，防止旧内核忽略新配置。
每次改变区域都会改变实际模型SHA/CRC，必须生成匹配的传输固件。

`make_candidate.py` 从已验证HLS62生成独立源码；`make_profile.py` 在新文件夹封存区域。
先保留/标定ROI内部的正确良品参照，再封装区域。当前标定工具不会自动寻找区域，
工程用例复用完整原始照片的旧参照，不能代替现场新花色标定。

验证分开记录：117原图默认模式回归；小型合成算术fixture的RTL三次事务；
四张已有实拍照片在两种合成外围背景中的8组工程测试。
后者保持原始840×840像素不变，仅检验背景隔离和坐标映射，不能当作新准确率样本。
实际CAD、上板状态见 `../../reports/v196/status.html`，不能从C/RTL通过推定上板成功。

```text
python experimental/input_roi_v196/make_candidate.py --out NEW_SOURCE
python experimental/input_roi_v196/make_profile.py --base BASE_PROFILE --out NEW_PROFILE --roi 80 70 840 840 --source-size 1000 1000
python experimental/input_roi_v196/validate.py --mode c --fixtures FIXTURES --profile NEW_PROFILE --compiled COMPILED_CHECK --out NEW_C_RECORDS
```

验收与部署仍需通过完整数值、时序、DRC、BIT/XSA/ELF身份及实际开发板核对。
候选与稳定工作站分开保存，不因新增ROI而放宽新输入的复核联锁。
