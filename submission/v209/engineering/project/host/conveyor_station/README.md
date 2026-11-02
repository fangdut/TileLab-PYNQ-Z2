# 匀速瓷砖模拟流水线

进入左侧检测区即截取瓷砖原生分辨率canvas帧，经网口送往PL。画面继续前进；未报警且身份、工位核验和自动处置校验有效时自动通过；报警到右侧复核区后停下，由人工复核。结果迟到也在右侧停下等待。

默认截图点到复核区4秒、175像素/秒。公开照片中的裂纹真实存在，输送动画为模拟，未接相机或机械执行器。红色区域是PL粗异常掩膜，由电脑叠加显示。HDMI可由电脑直连显示器，板上保留的视频模块不参与当前检测。

## 运行

推荐从完整V208工程包双击“启动流水线.cmd”。底层V202检测核心/固件/模型保持原哈希。新机器先在原工作站8793建立材质，完成3张不同良品和1张已知缺陷的工位核验并封存，然后在8794启动队列。

源码调用：start_conveyor.ps1 -Config 本次runtime中的station_config.json。该配置由原部署入口生成，不手写硬编码路径。Python由TILELAB_PYTHON或PATH提供；TILELAB_CHROME可指定Chrome。两台逻辑显示器须用扩展模式：电脑复核、外屏展示。显示页/display负责截帧，保持打开。

- 复核页 http://127.0.0.1:8794/；显示页 http://127.0.0.1:8794/display。
- 复核方式本次会话确认一次，下一工件保留；报警工件仍逐件点击结论。
- 正常自动通过的review=null，记录automatic_pass，不伪造人工复核。
- pause为本块后暂停；到站无有效结果不得通过；人工冲突使核验失效。
- restart_for_recording.ps1用于显式重新录制：保留原记录，未复核旧工件写明弃用原因，不虚构复核。open_recording_windows.ps1要求IDLE状态，并只重开项目浏览器窗口。
- PC本机状态读取可有限重试；上传/检测/复核/处置不自动重发。同一板卡只允许一个推理后端。

## 测试

在本目录用Python运行 python -m unittest -v test_flow.py test_policy.py test_station_api.py，共18项，不访问板卡。test_policy.py默认读取相邻stop_inspect_station目录，也可用TILELAB_STATION_SOURCE指定。

浏览器真实板端回放另用 npm install --no-save playwright，安装Chrome并提供ffmpeg（TILELAB_FFMPEG可指定），运行node accept_continuous.cjs。TILELAB_PLAYWRIGHT_MODULE可指定模块。该脚本会操作当前工件并明确标注非人工，仅用于主动验收；正式本人录制不运行它。accept_live.cjs仅保留为拒绝在V207及以上运行的历史脚本。

验证与测量范围见reports/v208。4秒是区域预留时间，约2.48～2.56秒是少量实板联调的截图至应用结果时间；约125ms/502ms是历史V202不同测量范围。不能混称产线吞吐。

## 许可

原创代码MIT；MVTec照片及派生参照遵循CC BY-NC-SA4.0；陶瓦照片遵循CC BY4.0；厂商源代码保留原许可。排除浏览器个人资料、runtime、录屏编码器及自动生成大文件。已收到参赛者设备实拍与工作站截图并补入V208报告；参赛者已提供剪辑后的演示视频用于官网提交，中英文海报已对齐当前流程。
