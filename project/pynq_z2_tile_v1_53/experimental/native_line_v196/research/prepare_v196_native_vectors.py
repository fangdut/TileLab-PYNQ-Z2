from pathlib import Path
import numpy as np,json,hashlib
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');O=W/'v196_native_vectors01';O.mkdir(exist_ok=False)
y,x=np.indices((224,79));a=(128+(x*7+y*13)%17-8).astype(np.int64);a[:,23:29]-=16;a.astype('uint8').tofile(O/'pixels.bin')
packed=np.zeros((79,3),dtype='<u8');thresholds=[1264,1858,2586]
for s,d in enumerate([2,4,8]):
    r=2*a[:,d:79-d]-a[:,:79-2*d]-a[:,2*d:];n=r.sum(0);e=np.abs(r).sum(0)
    alarm=n*n>=(thresholds[s]+1)*(e+1)
    packed[d:79-d,s]=(n&((1<<18)-1)).astype('u8')|(e.astype('u8')<<18)|(alarm.astype('u8')<<35)
packed.tofile(O/'expected.bin')
(O/'proof.json').write_text(json.dumps(dict(scope='INDEPENDENT_NUMPY_SYNTHETIC_ARITHMETIC_FIXTURE_NOT_PHOTO_ACCURACY',width=79,rows=224,thresholds=thresholds,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('*.bin')}),indent=2),encoding='utf8')
print('NATIVE_ARITHMETIC_FIXTURE_READY')
