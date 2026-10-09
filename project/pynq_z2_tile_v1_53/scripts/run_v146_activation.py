"""Launch PowerShell with file output so background services cannot retain pipes."""
from pathlib import Path
import datetime,hashlib,json,subprocess
R=Path(__file__).resolve().parents[1];O=R/'reports/v146';script=R/'scripts/activate_v146.ps1'
with (O/'activation.log').open('w',encoding='utf-8') as log:
    shell=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    p=subprocess.run([str(shell),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=50)
result=dict(exit_code=p.returncode,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),script_sha256=hashlib.sha256(script.read_bytes()).hexdigest())
(O/'activation_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert p.returncode==0
