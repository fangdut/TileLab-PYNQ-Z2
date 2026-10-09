from pathlib import Path
import sys,numpy as np
from PIL import Image
p=Path(__file__).resolve().parent.parent
raw=Path(sys.argv[1]);actual=np.frombuffer(raw.read_bytes(),dtype=np.uint8).reshape(720,1280,3)
yy,xx=np.indices((720,1280))
rgb=np.stack([(xx*3+yy*7+(xx//16)*51)%256,(xx*11+yy*5+(yy//9)*79)%256,(xx*7+yy*13)%256],axis=-1)
y=(rgb@np.array([77,150,29]))//256
kernel=np.array([[1,2,1],[2,4,2],[1,2,1]])
total=np.zeros((718,1278),dtype=np.int64)
for row in range(3):
 for col in range(3):total+=kernel[row,col]*y[row:row+718,col:col+1278]
expected=np.zeros((720,1280),dtype=np.uint8);expected[1:-1,1:-1]=total//16
assert np.array_equal(actual,np.repeat(expected[:,:,None],3,axis=2)), 'Gaussian independent image mismatch'
Image.fromarray(expected).save(p/'test_patterns/sim_epoch0_gaussian_expected.bmp')
Image.fromarray(actual).save(p/'reports/gaussian_rtl_simulation.bmp')
message='PASS GAUSSIAN IMAGE: all 921600 RGB pixels match independent NumPy weighted neighborhood, floor divide by 16, zero border. RTL simulation, NOT board capture.'
(p/'reports/gaussian_image_comparison.txt').write_text(message+'\n')
print(message)
