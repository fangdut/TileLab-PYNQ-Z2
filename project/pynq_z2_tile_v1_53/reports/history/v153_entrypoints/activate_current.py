"""Verify inherited artifacts, then program the connected board (volatile JTAG)."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / (ROOT.name + '.sdk')
OUT = ROOT / 'reports/v153'


def main():
    plan = json.loads((ROOT / 'ITERATION_PLAN.json').read_text(encoding='utf-8'))
    for name, digest in plan['inherited_hardware_sha256'].items():
        assert hashlib.sha256((SDK / name).read_bytes()).hexdigest() == digest, name
    # The packaged sealed manifest preserves provenance without requiring old
    # sibling projects to exist on the recipient's computer.
    baseline_manifest = hashlib.sha256((ROOT / 'reports/accepted_baseline/V1_52_DELIVERY_MANIFEST.json').read_bytes()).hexdigest()
    assert baseline_manifest == plan['baseline_manifest_sha256']
    for report in ('timing_summary.rpt', 'utilization.rpt', 'drc.rpt', 'cdc.rpt'):
        assert (ROOT / 'reports' / report).is_file(), report
    try:
        with urllib.request.urlopen('http://127.0.0.1:8770/api/live', timeout=2) as response:
            live = json.load(response)
    except urllib.error.URLError:
        live = None
    if live is not None:
        raise RuntimeError('A station already owns port 8770. Pause/settle/disconnect it before programming.')
    proof = ROOT / 'reports/programmed_v153.json'
    if proof.exists():
        prior = json.loads(proof.read_text())
        archived = OUT / ('programming_boot_' + str(prior['boot_id']) + '.json')
        if archived.exists():
            archived = OUT / ('programming_boot_' + str(prior['boot_id']) + '_' + str(proof.stat().st_mtime_ns) + '.json')
        if archived.exists():raise RuntimeError('Prior programming proof archive collision')
        archived.write_bytes(proof.read_bytes())
        proof.unlink()
    with (OUT / 'programming.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(['D:/2025.2/Vitis/bin/xsdb.bat', str(SDK / 'program_checked.tcl'), *sys.argv[1:]],
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0 and proof.exists(), 'Programming failed; see programming.log'
    record = json.loads(proof.read_text())
    for name in ('system.bit', 'system.xsa', 'hdmi_ethernet/build/hdmi_ethernet.elf'):
        assert record['sha256'][name] == hashlib.sha256((SDK / name).read_bytes()).hexdigest()
    print(json.dumps(dict(programmed=True, boot_id=record['boot_id'], artifact_hashes_verified=True)))


if __name__ == '__main__':
    main()
