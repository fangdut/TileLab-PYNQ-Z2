from pathlib import Path
import sys,json,numpy as np
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'models'))
from regions_reference import regions
out=r/'sim/region_vectors';out.mkdir(exist_ok=True)
cases=[]
a=np.zeros((256,512),np.uint8);cases.append(a.copy())
a[20:95,25:27]=1;a[110:210,370:373]=1;cases.append(a.copy())
a[:]=0
for x in range(20,480,50):a[30:101,x:x+2]=1
cases.append(a.copy())
a[:]=1;cases.append(a.copy())
a[:]=0;a[0:50,0]=1;a[230:256,510:512]=1;a[80,80]=1;cases.append(a.copy())
rng=np.random.default_rng(13);a=(rng.random((256,512))<0.04).astype(np.uint8);cases.append(a)
expected=[]
for i,a in enumerate(cases):
 (out/f'{i}.hex').write_text('\n'.join(map(str,a.ravel().tolist())))
 v=regions(a,shift=4);expected.append(v)
 words=[len(v['boxes'])|(256 if v['overflow'] else 0)]
 for box,n in zip(v['boxes'],v['areas']):words.extend([box[0]|box[1]<<16,box[2]|box[3]<<16,n])
 words.extend([0]*(25-len(words)))
 (out/f'{i}_expected.hex').write_text('\n'.join(f'{v:08x}' for v in words))
(out/'expected.json').write_text(json.dumps(expected,indent=2));print('Generated six independent region cases')
