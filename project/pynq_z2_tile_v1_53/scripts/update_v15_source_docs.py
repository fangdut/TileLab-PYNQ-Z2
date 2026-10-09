from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=R/'host/recipes.json';d=json.loads(p.read_text(encoding='utf-8'))
for r in d['recipes']:
 if r['id']=='mvtec_video_v15':r['name']='本机 H264 链路标定（历史对照）'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
p=R/'host/workstation.html';s=p.read_text(encoding='utf-8');s=s.replace("s.stimulus==='real_video'?'mvtec_video_v15'", "s.stimulus==='real_video'?'mvtec_hdmi_v15'")
s=s.replace('V1.5 在 FPGA 中识别产品经过，','运动源预加载照片后匀速渲染，无 H264 解码停顿；真实照片运动使用 HDMI 参数 89。V1.5 在 FPGA 中识别产品经过，')
p.write_text(s,encoding='utf-8')
p=R/'README.md';s=p.read_text(encoding='utf-8')
s=s.replace('本机静态 HDMI 89、本机视频链路 76','本机图像链路 89、历史 H264 视频链路 76')
s=s.replace('真实照片运动视频使用“本机视频链路纹理瓷砖标定”（76）','默认真实照片运动源也使用“本机 HDMI 纹理瓷砖标定”（89）；76 只保留作历史 H264 链路对照')
s=s.replace('## 工程与构建','默认 HDMI 运动源改为预加载纹理并按统一帧时钟渲染（host/ConveyorStimulus.cs），避免本机 H264 解码器启动时冻结并跳帧；不依赖每块砖停车，也不在电脑上检测。原 MP4 仍保留。Viewbox 统一映射到 1280×720，避免 Windows DPI 缩放裁切。失败诊断保存在 reports/v15/pre_player_fix。\n\n## 工程与构建',1)
p.write_text(s,encoding='utf-8')
