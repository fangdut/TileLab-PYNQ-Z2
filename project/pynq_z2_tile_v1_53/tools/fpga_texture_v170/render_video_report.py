"""Render recorded physical results. Display only; never run image detection."""
from pathlib import Path
import argparse,html,json


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    a=p.parse_args()
    def read(path):return json.loads(path.read_text())
    run=read(a.run/'progress.json');after=read(a.run/'hdmi117/summary.json')
    before=read(a.baseline/'summary.json');direct=read(a.run/'board117/summary.json')
    if run['status'] not in ['DEVELOPMENT_ACCURACY_PASS_SPEED_TARGET_PENDING','HDMI_ACCURACY_FAILED']:
        raise ValueError('Completed physical experiment required')
    results=read(a.run/'hdmi117/results.json');catalog=read(a.run/'hdmi117/plan.json')['photos']
    by_id={r['id']:r for r in results};photos={r['id']:r for r in catalog}
    fps=after['autonomous_hdmi_fps_over_photo_series'];duration=after['continuous_observation_seconds']
    labels={'good':'良品','crack':'裂纹','glue_strip':'胶条','gray_stroke':'灰色划痕','oil':'油污','rough':'粗糙缺陷'}
    cases=[]
    for key,ident,title in [('good','6621d769324f6e05d5838381','真实良品'),('crack','6621d769324f6e05d583835f','真实裂纹')]:
        proof=read(a.run/(key+'_snapshot/evidence.json'));audit=read(a.run/(key+'_reference_audit/audit.json'))
        if not audit['all_values_exact']:raise ValueError('Saved physical input audit failed')
        original=Path(photos[ident]['file']).as_uri()
        figures=''.join('<figure><img loading="lazy" src="'+html.escape(src)+'"><figcaption>'+caption+'</figcaption></figure>' for src,caption in [
            (original,'数据集原始实拍照片'),(key+'_snapshot/actual_hdmi_input.png','FPGA 校正后实际采集图'),
            (key+'_snapshot/actual_pl_overlay.png','FPGA 掩膜的显示叠加')])
        cases.append(f'<section><h2>{title}</h2><p>板上分数 {proof["pl_peak"]}，阈值 {proof["pl_threshold"]}，判定为'+('缺陷' if proof['pl_image_alarm'] else '正常')+'。评分和全部掩膜像素与独立参考一致。</p><div class="photos">'+figures+'</div></section>')
    rows=[]
    for r in results:
        label=labels.get(r['label'],r['label']);decision='缺陷' if r['alarm'] else '正常'
        rows.append('<tr class="'+('ok' if r['correct'] else 'bad')+'"><td>'+html.escape(r['id'])+'</td><td>'+html.escape(label)+f'</td><td>{r["peak"]}</td><td>{decision}</td><td>'+('正确' if r['correct'] else '错误')+'</td></tr>')
    content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TileLab V172 实板 HDMI 真实照片复测</title><style>
body{{font-family:"Microsoft YaHei",system-ui,sans-serif;color:#1b2d40;background:#f2f5f8;margin:0;line-height:1.7}}main{{max-width:1120px;margin:auto;padding:34px 24px}}h1{{font-size:30px;margin:0}}h2{{font-size:21px}}.sub{{color:#52657a}}section,.notice,.metrics{{background:white;border:1px solid #dde4eb;border-radius:12px;padding:22px;margin:20px 0}}.notice{{background:#fff8e8}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.value{{font-size:29px;font-weight:700;color:#125c92}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #e3e8ef}}th{{background:#edf3f8}}.photos{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}figure{{margin:0}}img{{width:100%;display:block;border-radius:7px}}figcaption{{color:#52657a;font-size:13px;margin-top:7px}}.bad{{background:#fff0ef}}a{{color:#1265a0}}details{{margin:20px 0}}.scroll{{overflow:auto}}@media(max-width:700px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.photos{{grid-template-columns:1fr}}h1{{font-size:24px}}}}
</style><main><h1>FPGA 实板复测 · V172</h1><p class="sub">真实瓷砖表面照片经 HDMI 输入，由 FPGA 完成颜色校正与检测。</p>
<div class="metrics"><div>HDMI 图片判对<div class="value">{after['correct']} / {after['cases']}</div></div><div>良品误报<div class="value">{after['normal_false_alarms']} / {after['normal_images']}</div></div><div>缺陷检出<div class="value">{after['anomalies_detected']} / {after['anomalies']}</div></div><div>持续检测速度<div class="value">{fps:.2f} FPS</div></div></div>
<div class="notice">这些是反复使用的 MVTec Tile 公开开发集，不能代表独立盲测或任意彩绘／多材质表现。尚未达到持续 10 FPS 目标。图片判定通过也不代表细裂纹逐像素定位达标。</div>
<section><h2>同一批 117 张照片，校正前后对照</h2><table><thead><tr><th>指标</th><th>未校正 HDMI</th><th>FPGA 颜色校正后</th></tr></thead><tbody>
<tr><td>图片判对</td><td>{before['correct']} / {before['cases']}</td><td>{after['correct']} / {after['cases']}</td></tr>
<tr><td>良品误报</td><td>{before['normal_false_alarms']} / {before['normal_images']}</td><td>{after['normal_false_alarms']} / {after['normal_images']}</td></tr>
<tr><td>缺陷检出</td><td>{before['anomalies_detected']} / {before['anomalies']}</td><td>{after['anomalies_detected']} / {after['anomalies']}</td></tr>
<tr><td>裂纹检出</td><td>{before['cracks_detected']} / {before['cracks']}</td><td>{after['cracks_detected']} / {after['cracks']}</td></tr></tbody></table>
<p>模型与阈值保持不变；颜色参数来自独立灰阶图。逐像素校正、特征提取与判定均在 FPGA 内完成。</p></section>
{''.join(cases)}
<section><h2>硬件运行记录</h2><p>连续观察 {duration:.1f} 秒，FPGA 自主完成 {after['autonomous_frames_in_interval']} 次检测，平均 {fps:.3f} 次／秒。检测期间两个 ARM 核保持暂停，共检查 {after['arm_halt_checks']} 次；电脑只播放输入、读取记录和显示结果。</p><p>原始照片直接送入检测核的独立数值回归：{direct['correct']} / {direct['cases']}，评分和掩膜逐值一致；固定帧速度 {direct['autorestart_fixed_frame_fps']:.3f} FPS。</p>
<p><a href="hdmi117/summary.json">HDMI 实验汇总</a> · <a href="hdmi117/results.json">全部原始记录</a> · <a href="color_profile.json">独立标定参数</a> · <a href="program/identity.json">下载身份记录</a></p></section>
<details><summary>查看 117 张逐图判定</summary><div class="scroll"><table><thead><tr><th>原始照片 ID</th><th>标注</th><th>硬件分数</th><th>硬件判定</th><th>结果</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>
<p class="sub">照片来自 MVTec AD Tile 原始实拍数据，保留原始文件 SHA256 和来源链接；数据及相关派生证据遵循 CC BY-NC-SA 4.0。灰阶标定图仅为测试夹具，不计入真实照片准确率。</p></main></html>'''
    (a.run/'report.html').write_text(content,encoding='utf8')
    print(str(a.run/'report.html'))


if __name__=='__main__':main()
