from pathlib import Path
import sys,json,numpy as np
from PIL import Image
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'models'))
from regions_reference import regions
from valley_reference import detect
out=r/'sim/region_full_vectors';out.mkdir(exist_ok=True)
cases=[np.zeros((720,1280),np.uint8),detect(Image.open(r/'data/conveyor/station_4.png'),threshold=36)[0].astype(np.uint8),np.ones((720,1280),np.uint8)]
expected=[]
for i,a in enumerate(cases):
 (out/f'{i}.hex').write_text('\n'.join(map(str,a.ravel().tolist())))
 v=regions(a);expected.append(v);words=[len(v['boxes'])|(256 if v['overflow'] else 0)]
 for box,n in zip(v['boxes'],v['areas']):words.extend([box[0]|box[1]<<16,box[2]|box[3]<<16,n])
 words.extend([0]*(25-len(words)));(out/f'{i}_expected.hex').write_text('\n'.join(f'{x:08x}' for x in words))
(out/'expected.json').write_text(json.dumps(expected,indent=2))
s=(r/'sim/tb_region_grid.sv').read_text().replace('tb_region_grid','tb_region_full').replace('.WIDTH(512),.HEIGHT(256),.SHIFT(4)', '.WIDTH(1280),.HEIGHT(720),.SHIFT(5)').replace('131071','921599').replace('testno<6','testno<3').replace('/region_vectors/','/region_full_vectors/').replace('y<256','y<720').replace('x<512','x<1280').replace('y*512+x','y*1280+x').replace('repeat(120)','repeat(370)').replace('#30000000','#100000000').replace('786432','2764800')
(r/'sim/tb_region_full.sv').write_text(s)
s=(r/'scripts/test_regions.tcl').read_text().replace('region_test','region_full_test').replace('/region_sim','/region_full_sim').replace('tb_region_grid','tb_region_full')
(r/'scripts/test_regions_full.tcl').write_text(s)
