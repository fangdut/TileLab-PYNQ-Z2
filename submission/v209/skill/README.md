# 可复用校验技能包

本目录为竞赛3.3.5.2所指的技能包，由校验脚本、失败定位流程和验证记录组成。它不是Python语言的一项标准功能，也不是已验证的PYNQ Overlay/DMA插件。陌生队伍可只复制本目录；脚本不含瓷砖模型、板卡IP地址或寄存器地址。

|技能|适用场景与使用方法|已验证效果|来源观察与失效条件|
|---|---|---|---|
|verify_files.py|任意文件包的bytes/SHA256清单。`python verify_files.py package_dir`，清单为package_dir/manifest.json|验证记录见verification.json，含独立通信帧目录的正确/损坏/越界路径用例|旧部署或损坏文件容易与当前结果混用。清单本身不可信时不能证明作者、来源或硬件正确|
|compare_arrays.py|DSP、通信或定点算子的黄金参考比对。`python compare_arrays.py --expected ref.npy --actual out.npy --out result.json`|独立音频滤波样例、位错误、shape/dtype不一致用例。相同退出0，不同或不适用退出非零|早期输入域及像素来源不一致。禁止隐式裁边、改dtype或放宽阈值。不能证明数组来自板卡|
|verify_bundle.py|SHA256部署清单及XSA内嵌BIT配对。`python verify_bundle.py --manifest deploy.json --root board_dir`|独立合成打包样例与当前真实BIT/XSA配对，见verification.json|旧XSA不能证明新BIT。清单值须是SHA256字符串，与verify_files的对象格式不同。不能代替时序或上板测试|

Python3.10及以上。verify_files和verify_bundle仅用标准库，compare_arrays另需NumPy。复用验证运行 `python run_reuse_checks.py --out path_to_new_verification.json --bundle path_to_restored_engineering`。输出必须是新文件，避免覆盖旧证据。

## 提炼与边界

从旧结果误关联、部署文件混配、显示像素与原图不一致、超时后盲重发等观察中，提炼出精确比对、版本绑定和不重放非幂等操作的规则。详见pitfalls.md与../report/llm_collaboration.md。脚本复用验证采用新的独立临时目录和不同任务数据，未在另一台电脑或另一块开发板完成物理部署。不得将这些结果写成跨板PYNQ验收。

指南的PYNQ Skill是面向PYNQ框架的可复用技能。PYNQ-Z2是板卡型号；本项目当前PS侧为C固件、PC侧为Python，没有使用PYNQ Python Overlay加载或DMA接口，因此仅提交普通可复用校验技能包，不声称已取得通用PYNQ Skill的额外验证。
