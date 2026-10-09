"""Compatibility entry point: V1.6 uses only the SG Ethernet application."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('rebuild_ethernet.py')),run_name='__main__')
