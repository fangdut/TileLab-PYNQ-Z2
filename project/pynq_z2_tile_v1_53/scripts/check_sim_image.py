from pathlib import Path
import sys, numpy as np
from PIL import Image
p=Path(__file__).resolve().parent.parent
raw=Path(sys.argv[1]);a=np.frombuffer(raw.read_bytes(),dtype=np.uint8).reshape(720,1280,3)
b=np.asarray(Image.open(p/'test_patterns/sim_epoch0_sobel_expected.bmp'))
assert np.array_equal(a,np.repeat(b[:,:,None],3,axis=2)), 'RTL pixels differ from independent NumPy Sobel model'
Image.fromarray(a).save(p/'reports/sobel_rtl_simulation.bmp')
(p/'reports/image_comparison.txt').write_text('PASS IMAGE: all 921600 Sobel RGB pixels match independent NumPy centered, zero-border, saturating golden model. Source is RTL simulation, NOT board capture.\n')
print('PASS IMAGE: 921600 pixels, 2764800 bytes exactly equal to independent NumPy golden image')
