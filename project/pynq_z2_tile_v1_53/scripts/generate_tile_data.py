"""Reproducible synthetic inputs and exact procedural crack masks, not real photos."""
from pathlib import Path
import json,sys,hashlib,subprocess
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'models'),str(ROOT/'host/_deps')]
from tile_reference import detect,metrics
W,H=1280,720
OUT=ROOT/'data/synthetic';OUT.mkdir(parents=True,exist_ok=True)

def sample(idx):
    rng=np.random.default_rng(2026092200+idx)
    crack=idx%2==1;brightness=(90,130,175,220)[idx//2%4]
    yy,xx=np.indices((H,W));base=brightness+((xx-W/2)/W)*(idx%3)*20
    base=base+rng.normal(0,1.2,(H,W));a=np.clip(base,0,255).astype(np.uint8)
    rgb=Image.fromarray(np.repeat(a[:,:,None],3,axis=2));d=ImageDraw.Draw(rgb)
    truth=Image.new('L',(W,H));t=ImageDraw.Draw(truth)
    family=idx//8%4
    # Known difficult negative cases are retained, never silently removed.
    if family==1:
        for x in range(180,1100,100):d.line((x,100,x+55,620),fill=(brightness-18,)*3,width=3)
    if family==2:
        d.ellipse((300,250,520,430),fill=(max(0,brightness-55),)*3)
    if family==3:
        d.rectangle((850,180,1050,400),fill=(min(255,brightness+45),)*3)
    width=(1,2,3,5,8)[idx//2%5]
    if crack:
        x=int(rng.integers(540,760));pts=[]
        for y in range(130,600,25):
            x=max(430,min(900,x+int(rng.integers(-16,17))));pts.append((x,y))
        dark=max(0,brightness-(45,80,120)[idx//3%3])
        d.line(pts,fill=(dark,)*3,width=width);t.line(pts,fill=255,width=width)
        branch=[pts[8],(pts[8][0]+60,pts[8][1]+30),(pts[8][0]+105,pts[8][1]+100)]
        d.line(branch,fill=(dark,)*3,width=max(1,width//2));t.line(branch,fill=255,width=max(1,width//2))
    return rgb,truth,dict(crack=crack,seed=2026092200+idx,width=width if crack else 0,
                         nuisance=('plain','faint_pattern','dark_stain','reflection')[family],brightness=brightness)

rows=[]
for idx in range(96):
    rgb,truth,meta=sample(idx);stem=f'tile_{idx:03d}'
    rgb.save(OUT/(stem+'.png'));truth.save(OUT/(stem+'_truth.png'))
    mask,result=detect(rgb);trutharray=np.asarray(truth)>0
    yy,xx=np.where(trutharray);truthbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if len(xx) else None
    row=dict(id=stem,image='synthetic/'+stem+'.png',truth='synthetic/'+stem+'_truth.png',
             split='calibration' if idx<32 else 'heldout_synthetic',truth_box=truthbox,
             **meta,**result,metrics=metrics(mask,trutharray))
    rows.append(row)
(ROOT/'data/manifest.json').write_text(json.dumps(dict(origin='PROCEDURAL_SYNTHETIC',
    note='96 synthetic inputs and masks, not camera photographs or real-world accuracy',items=rows),indent=2),encoding='utf8')
summary=[]
for split in ('calibration','heldout_synthetic'):
    cases=[r for r in rows if r['split']==split]
    tp=sum(r['crack'] and r['alarm'] for r in cases);fp=sum(not r['crack'] and r['alarm'] for r in cases)
    fn=sum(r['crack'] and not r['alarm'] for r in cases);tn=sum(not r['crack'] and not r['alarm'] for r in cases)
    summary.append(dict(split=split,n=len(cases),tp=tp,fp=fp,fn=fn,tn=tn,recall=tp/(tp+fn),false_alarm_rate=fp/(fp+tn)))
(ROOT/'reports/synthetic_metrics.json').write_text(json.dumps(dict(mode='OFFLINE_REFERENCE_ONLY',threshold=12,results=summary),indent=2))
print(json.dumps(summary))

if '--video' in sys.argv:
    import imageio_ffmpeg
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    # Static image sequence is suitable for first board qualification.
    ids=[0,1,4,5,16,17];frames=[np.asarray(Image.open(OUT/f'tile_{i:03d}.png')) for i in ids]
    def writer(name):
        return subprocess.Popen([exe,'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','60','-i','-',
          '-an','-c:v','libx264','-preset','veryfast','-crf','12','-pix_fmt','yuv420p',str(ROOT/'data'/name)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    p=writer('hdmi_stationary_SYNTHETIC_720p60.mp4')
    for a in frames:
        for f in range(120):p.stdin.write(a.tobytes())
    p.stdin.close();err=p.stderr.read();assert p.wait()==0,err.decode(errors='replace')
    # Moving tile edges intentionally form a harder test, not an advertised pass.
    tile,_,_=sample(5);tile=tile.resize((640,360))
    p=writer('hdmi_motion_CHALLENGE_720p60.mp4');motion=[]
    for n in range(600):
        img=Image.new('RGB',(W,H),(45,45,45));x=(n*8)%1920-640;img.paste(tile,(x,180))
        p.stdin.write(np.asarray(img).tobytes());motion.append(dict(frame=n,tile_x=x,tile_y=180,origin='SYNTHETIC_CHALLENGE'))
    p.stdin.close();err=p.stderr.read();assert p.wait()==0,err.decode(errors='replace')
    (ROOT/'data/motion_frames.json').write_text(json.dumps(motion))
    image=ROOT/'data/ai_tile_crack_SYNTHETIC.png'
    if image.exists():
        subprocess.run([exe,'-y','-loop','1','-i',str(image),'-t','8','-r','60','-vf','scale=1280:720',
                        '-c:v','libx264','-crf','12','-pix_fmt','yuv420p',str(ROOT/'data/hdmi_photo_AI_SYNTHETIC_720p60.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    print('Three SYNTHETIC/CHALLENGE HDMI videos generated; not board outputs')
