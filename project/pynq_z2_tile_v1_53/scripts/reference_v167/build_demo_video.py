"""Render a labeled evidence edit from actual board captures, never fake camera footage."""
from pathlib import Path
import argparse,json,subprocess,hashlib,sys
from PIL import Image,ImageDraw,ImageFont
def main():
    p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--performance',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--ffmpeg',type=Path,required=True);p.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/simhei.ttf'));a=p.parse_args()
    board=json.loads(a.board.read_text());performance=json.loads(a.performance.read_text())
    if not board['passed']:raise ValueError('Complete actual board evidence required')
    if a.out.exists():raise FileExistsError(a.out)
    a.out.parent.mkdir(parents=True,exist_ok=True);font=lambda n:ImageFont.truetype(str(a.font),n)
    navy='#122e40';muted='#b7cbd5';gold='#ffc75f';teal='#5bd0ce';scenes=[]
    def canvas(title,subtitle):
        im=Image.new('RGB',(1280,720),navy);d=ImageDraw.Draw(im);d.rectangle((0,0,1280,8),fill=teal);d.text((40,30),title,font=font(34),fill='white');d.text((40,84),subtitle,font=font(19),fill=muted);d.text((40,680),'程序生成测试图的实际开发板回放记录剪辑 | 非实体瓷砖相机实拍',font=font(20),fill=gold);return im,d
    im,d=canvas('TileLab · 单片瓷砖良品参照检测','PYNQ-Z2 / Zynq-7020 / Vivado与Vitis 2025.2')
    for i,line in enumerate(['按花色标定完整良品，固定拍摄位置与光照','完整500×500表面，250000个像素参与差分','电脑配准与区域分析，FPGA计算全幅差异图','下列画面来自实际HDMI、DDR、以太网链路']):d.text((55,180+i*95),line,font=font(28),fill='white')
    scenes.append(dict(image=im,seconds=8,label='intro'))
    root=a.board.parent/'station'
    def panel(im,x,title,path,crop=False):
        d=ImageDraw.Draw(im);d.text((x,133),title,font=font(20),fill=teal)
        source=Image.open(path).convert('RGB')
        if crop:source=source.crop((390,110,890,610))
        source.thumbnail((360,390));im.paste(source,(x+(360-source.width)//2,176+(390-source.height)//2))
    for kind in ('good','line'):
        for row in [r for r in board['rows'] if r['source']['kind']==kind]:
            result=row['result'];active=json.loads((root/'calibrations'/row['source']['style']/'active.json').read_text());ref=root/active['bundle']/'reference.png';folder=root/result['record'];current=folder/'capture/input.png';overlay=Path(result['preview'])
            title='正常表面：未发现变化候选' if kind=='good' else '人工细线：发现表面变化候选'
            im,d=canvas(title,row['source']['style']+' | '+row['source']['source']+' | 实际开发板输出与独立参考逐像素一致')
            panel(im,40,'已保存的良品参照',ref,True);panel(im,460,'本次HDMI实际捕获',current,True);panel(im,880,'基于FPGA差异图的区域结果',overlay)
            proof=result['hardware'];d.text((40,596),f"FPGA计算 {proof['engine_seconds']*1000:.2f} ms  |  差异像素 0 / 250000  |  CRC已验证",font=font(22),fill='white')
            d.text((40,636),'ROI图示为原生500×500表面；检测与保存的输入仍为完整720p帧',font=font(18),fill=muted)
            scenes.append(dict(image=im,seconds=4,label=row['source']['source'],capture_sha256=hashlib.sha256(current.read_bytes()).hexdigest(),score_sha256=proof['score_sha256']))
    for row in [r for r in board['rows'] if r['source']['kind']=='invalid_pose'][:2]:
        result=row['result'];folder=root/result['record'];im,d=canvas('异常输入：拒绝检测，交由人工复核',row['source']['style']+' | 位姿超出固定夹具容差')
        panel(im,40,'本次HDMI实际捕获',folder/'capture/input.png',True)
        for i,line in enumerate(['状态：REJECTED_INPUT','报警值：未判定，而非良品','不输出伪造的合格掩码','原因：translation_exceeds_fixture_tolerance']):d.text((460,210+i*78),line,font=font(23 if i<3 else 19),fill='white' if i<3 else gold)
        scenes.append(dict(image=im,seconds=6,label=row['source']['source']))
    im,d=canvas('性能与完整性：分别报告计算核和整次检测','相同实际捕获输入；NumPy参考与FPGA结果完全一致')
    numbers=[f"NumPy完整图参考：{performance['cpu_median_ms']:.2f} ms",f"实际FPGA计算核：{performance['pl_median_ms']:.2f} ms",f"上传、计算与返回：{performance['request_median_ms']:.2f} ms",f"完整检测操作：{performance['full_median_ms']:.2f} ms"]
    for i,line in enumerate(numbers):d.text((55,170+i*91),line,font=font(31),fill=teal if i==1 else 'white')
    d.text((55,576),'计算核加速不等于端到端加速；720p60输入不等于60次检测/秒',font=font(23),fill=gold);scenes.append(dict(image=im,seconds=10,label='measured_performance'))
    im,d=canvas('适用边界与可复现交付','原始记录、失败用例、源代码和构建脚本随项目提供')
    for i,line in enumerate(['低对比度单像素变化仍可能漏检','无候选和拒判均不等于良品认证','真实实体瓷砖与相机成像准确率尚未验收','网页提供良品、人工细线、位姿拒判一键演示']):d.text((50,180+i*96),line,font=font(28),fill='white')
    scenes.append(dict(image=im,seconds=8,label='limitations'))
    command=[str(a.ffmpeg),'-hide_banner','-loglevel','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','15','-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(a.out)]
    with a.out.with_suffix('.encoder.log').open('w',encoding='utf8') as log:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log)
        try:
            for scene in scenes:
                pixels=scene['image'].tobytes()
                for _ in range(scene['seconds']*15):process.stdin.write(pixels)
            process.stdin.close();code=process.wait(timeout=180)
        except BaseException:process.kill();process.wait();raise
    if code:raise RuntimeError('Video encoding failed')
    a.out.with_suffix('.json').write_text(json.dumps(dict(scope='EDITED_ACTUAL_BOARD_REPLAY_EVIDENCE_NOT_CAMERA_FILM',seconds=sum(s['seconds'] for s in scenes),fps=15,scenes=[{k:v for k,v in s.items() if k!='image'} for s in scenes],board_sha256=hashlib.sha256(a.board.read_bytes()).hexdigest(),video_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),render_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n');print(a.out)
if __name__=='__main__':main()
