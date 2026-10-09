"""V1.6 default application uses continuous SG capture and Ethernet."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("build_ethernet.py")),run_name="__main__")
