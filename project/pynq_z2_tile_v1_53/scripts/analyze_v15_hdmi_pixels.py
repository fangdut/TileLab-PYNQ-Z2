"""Diagnose input-path radiometry; no label-driven threshold optimization."""
from pathlib import Path
import numpy as np,json
from PIL import Image
R=Path(__file__).resolve().parents[1]
rows=[]
for i in range(17):
    a=np.asarray(Image.open(R/f'data/real_tiles/hdmi/real_{i:03d}.png').convert('RGB'),dtype=np.float32)
    b=np.asarray(Image.open(R/f'reports/v15/real_board/real_{i:03d}_original.png').convert('RGB'),dtype=np.float32)
    src=a[110:610,390:890].reshape(-1,3);got=b[110:610,390:890].reshape(-1,3)
    fits=[]
    for c in range(3):
        slope,offset=np.linalg.lstsq(np.column_stack([src[:,c],np.ones(len(src))]),got[:,c],rcond=None)[0]
        err=got[:,c]-(src[:,c]*slope+offset)
        fits.append(dict(slope=float(slope),offset=float(offset),rmse=float(np.sqrt((err*err).mean())),min=float(got[:,c].min()),max=float(got[:,c].max())))
    rows.append(dict(index=i,channels=fits))
out=dict(scope='Measured source PNG to captured HDMI RGB mapping, no class labels used',items=rows)
(R/'reports/v15/hdmi_radiometry.json').write_text(json.dumps(out,indent=2));print(json.dumps(rows[0]))
