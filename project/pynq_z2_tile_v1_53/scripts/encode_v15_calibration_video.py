"""Normal-only calibration video; unrelated to continuous conveyor acceptance."""
from pathlib import Path
import sys,subprocess
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host/_deps'));import imageio_ffmpeg
paths=[R/f'data/calibration_hdmi/calib_{n:03d}.png' for n in range(230)];assert all(p.exists() for p in paths)
lst=R/'data/calibration_hdmi/train.ffconcat'
lst.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration 0.6\n" for p in paths)+f"file '{paths[-1].as_posix()}'\n")
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-r','60','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','12','-pix_fmt','yuv420p',str(R/'data/calibration_hdmi_video.mp4')],check=True)
print('Encoded 230 normal training images; 0.6 second per identity; calibration, not conveyor acceptance')
