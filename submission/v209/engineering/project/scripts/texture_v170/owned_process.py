"""Bound a CAD command's lifetime, including children left by Windows launchers."""
import os
import signal
import subprocess


def run_owned(args, *, timeout, **kwargs):
    """Like run(check=False), but terminate the owned process tree on timeout.

    Keep the root alive until tree termination: subprocess.run kills that root
    first on timeout, which can orphan Vivado's launcher and router on Windows.
    Never select processes by executable name or affect unrelated CAD runs.
    """
    if os.name != 'nt':
        kwargs['start_new_session'] = True
    with subprocess.Popen(args, **kwargs) as proc:
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            try:
                if os.name == 'nt':
                    cleanup = subprocess.run(
                        ['taskkill.exe', '/PID', str(proc.pid), '/T', '/F'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=30)
                    expired.tree_cleanup = dict(pid=proc.pid,
                        returncode=cleanup.returncode, output=cleanup.stdout)
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                    expired.tree_cleanup = dict(pid=proc.pid, returncode=0)
            except Exception as cleanup_error:
                expired.tree_cleanup = dict(pid=proc.pid, error=repr(cleanup_error))
            finally:
                # Fallback only for our root if platform tree cleanup failed.
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=10)
            raise
        return subprocess.CompletedProcess(args, code)
