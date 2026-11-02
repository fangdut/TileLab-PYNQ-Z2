"""Exercise a real Windows child tree; never touches Vivado or the board."""
from pathlib import Path
import ctypes
import os
import subprocess
import sys
import tempfile
import unittest
from owned_process import run_owned


class OwnedProcessTest(unittest.TestCase):
    def test_normal_completion(self):
        self.assertEqual(run_owned([sys.executable, '-c', 'raise SystemExit(3)'],
                                   timeout=5).returncode, 3)

    @unittest.skipUnless(os.name == 'nt', 'Windows process tree regression')
    def test_timeout_kills_descendant_preserves_unrelated_process(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        try:
            with tempfile.TemporaryDirectory() as directory:
                pid_file = Path(directory)/'child.pid'
                code = ('import subprocess,sys,time;from pathlib import Path;'
                        'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);'
                        'Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)')
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    run_owned([sys.executable, '-c', code, str(pid_file)], timeout=2)
                self.assertEqual(caught.exception.tree_cleanup['returncode'], 0)
                child = int(pid_file.read_text())
                handle = kernel.OpenProcess(0x100000, False, child)
                if handle:
                    try:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 0), 0)
                    finally:
                        kernel.CloseHandle(handle)
                self.assertIsNone(sentinel.poll(), 'Unrelated process was killed')
        finally:
            sentinel.terminate()
            sentinel.wait(timeout=5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
