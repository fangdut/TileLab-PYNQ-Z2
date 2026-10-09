from pathlib import Path
import json,hashlib,subprocess
import numpy as np
from PIL import Image
from reportlab.graphics.shapes import Drawing,String,Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor
R=Path(__file__).resolve().parents[1];T=R/'reports/v15'
old=json.loads((T/'pre_gate_band/motion_evidence_audit.json').read_text());event=old['real']['items'][1];path=R/'review_records'/(event['key']+'.png')
timeline=json.loads((R/'data/real_tiles/video_manifest.json').read_text())['timeline'];tile=next(x for x in timeline[event['code']]['visible'] if x['x']<=640<x['x']+500)
a=np.asarray(Image.open(path),dtype=np.int32);counts=(a[110:610,:,0]+2*a[110:610,:,1]+a[110:610,:,2]>=320).sum(axis=0);band=np.convolve(counts,np.ones(64)/64,'same');left=tile['x'];xx=list(range(32,468))
d=Drawing(680,305);plot=LinePlot();plot.x=55;plot.y=78;plot.width=600;plot.height=185
plot.data=[[(x,int(counts[left+x])) for x in xx],[(x,float(band[left+x])) for x in xx],[(32,200),(467,200)]]
plot.xValueAxis.valueMin=0;plot.xValueAxis.valueMax=500;plot.xValueAxis.valueSteps=list(range(0,501,100));plot.yValueAxis.valueMin=100;plot.yValueAxis.valueMax=500;plot.yValueAxis.valueSteps=list(range(100,501,100))
plot.xValueAxis.labels.fontName='Helvetica';plot.yValueAxis.labels.fontName='Helvetica';plot.xValueAxis.labels.fontSize=14;plot.yValueAxis.labels.fontSize=14
colors=['#B17638','#087D77','#AD4141']
for n,color in enumerate(colors):plot.lines[n].strokeColor=HexColor(color);plot.lines[n].strokeWidth=1 if n!=1 else 2
plot.lines[2].strokeDashArray=[4,3];d.add(plot)
d.add(String(55,280,'Bright pixels per column',fontName='Helvetica',fontSize=14));d.add(String(265,34,'Photo x position (pixels)',fontName='Helvetica',fontSize=14))
for x,n,label in [(55,0,'Single column'),(245,1,'64-column average'),(475,2,'Threshold 200')]:
 d.add(Line(x,14,x+25,14,strokeColor=HexColor(colors[n]),strokeWidth=2));d.add(String(x+31,10,label,fontName='Helvetica',fontSize=14))
svg=T/'gate_diagnostic.svg';svg.write_text(renderSVG.drawToString(d).replace('font-family: Helvetica;', 'font-family: Arial, sans-serif;'),encoding='utf-8')
base=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies';node=base/'node/bin/node.exe';sharp=(base/'node/node_modules/sharp').as_posix()
subprocess.run([str(node),'-e',f"require('{sharp}')(process.argv[1],{{density:220}}).flatten({{background:'#ffffff'}}).png().toFile(process.argv[2])",str(svg),str(T/'gate_diagnostic.png')],check=True)
(T/'gate_figure_source.json').write_text(json.dumps(dict(key=event['key'],image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),single_min=int(counts[left+32:left+468].min()),band_mean_min=float(band[left+32:left+468].min()),interpretation='Spatial sweep across actual captured RGB, not a sampled time series; no detector image smoothing applied'),indent=2))
