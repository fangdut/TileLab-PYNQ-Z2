from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1]
evidence=R/'reports/weak_crack/guard_comparison.json'
guard_sha=hashlib.sha256(evidence.read_bytes()).hexdigest()
recipes=[dict(id='synthetic_v16',name='合成表面 · 弱裂纹增强',threshold=36,requires_weak_support=True,description='两级邻域支持；高阈值 36、低阈值 18。合成演示参数，真实纹理需单独标定。',calibration_sha256=None),dict(id='mvtec_hdmi_weak_v16',name='本机 HDMI 瓷砖 · 弱裂纹增强',threshold=89,requires_weak_support=True,description='高阈值 89、低阈值 45；两级 3×3 邻域支持至少 3 点。已检查 230 张历史实采正常训练图；历史回归不代表盲测准确率。',calibration_sha256=guard_sha,scope='Current HDMI pipeline at 500px texture scale; historical regression architecture selection')]
(R/'host/recipes.json').write_text(json.dumps(dict(version=2,default='mvtec_hdmi_weak_v16',recipes=recipes),ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('workstation.py','workstation.html'):
 p=R/'host'/name;s=p.read_text(encoding='utf-8').replace('synthetic_v14','synthetic_v16').replace('mvtec_hdmi_v15','mvtec_hdmi_weak_v16')
 if name.endswith('.py'):
  s=s.replace("self.recipe_id='synthetic_v16'","self.recipe_id='mvtec_hdmi_weak_v16'").replace('self.threshold=36;','self.threshold=89;')
 else:
  s=s.replace('请求阈值 ${s.threshold} · 当前证据帧阈值 ${s.applied_threshold??\'—\'}','请求高阈值 ${s.threshold} · 实采高/低 ${s.applied_threshold??\'—\'}/${s.frame?.applied_low_threshold??\'—\'}')
  s=s.replace('算法：四方向暗谷检测 / PL 流水线 / 全分辨率帧缓存','算法：四方向暗谷 + 双阈值 + 两级邻域支持 / 全部在 FPGA')
  s=s.replace('裂痕灵敏度阈值','裂痕高阈值（低阈值自动取一半）')
  s=s.replace('阈值越低越敏感。参数在瓷砖间隙提交，随后在新帧边界生效。','高阈值找强响应；低阈值为其一半，弱点须有至少 3 个邻域候选支持。参数在瓷砖间隙提交。')
 p.write_text(s,encoding='utf-8')
print('V1.6 host provenance and material recipe configured')
