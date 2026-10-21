"""Run independent arithmetic, AXI configuration and integrated video RTL checks."""
from pathlib import Path
import argparse, hashlib, json, subprocess, time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    base = root / 'experimental/video_v171'
    rtl = base / 'rtl'
    cases = {
        'color_correct': ['video_color_correct.sv'],
        'video_regs': ['video_regs.v'],
        'pipeline': ['video_color_correct.sv', 'video_roi_tokens.sv',
                     'video_capture_link.sv', 'roi_ddr_writer.sv',
                     'pl_frame_scheduler.sv', 'pl_result_latch.sv',
                     'hdmi_detector_pipeline.v'],
    }
    results = []
    for name, files in cases.items():
        out = a.out / name
        out.mkdir()
        sources = [rtl / f for f in files] + [base / 'sim' / ('tb_' + name + '.sv')]
        commands = [
            ['xvlog.bat', '-sv', *map(str, sources),
             'D:/2025.2/Vivado/data/verilog/src/glbl.v'],
            ['xelab.bat', 'tb_' + name, 'glbl', '-L', 'xpm', '-L', 'unisims_ver',
             '-s', 'test', '-debug', 'typical'],
            ['xsim.bat', 'test', '-runall'],
        ]
        start = time.time()
        for cmd in commands:
            cmd[0] = 'D:/2025.2/Vivado/bin/' + cmd[0]
            with (out / (Path(cmd[0]).stem + '_console.log')).open('w') as log:
                run = subprocess.run(cmd, cwd=out, stdout=log, stderr=subprocess.STDOUT)
            if run.returncode:
                raise RuntimeError(f'{name}: {cmd[0]} failed; inspect {out}')
        log_text = (out / 'xsim_console.log').read_text(errors='replace')
        if 'PASS' not in log_text or 'Fatal:' in log_text or 'Error:' in log_text:
            raise RuntimeError(f'{name}: no clean PASS marker; inspect {out}')
        result = dict(test=name, passed=True, seconds=time.time()-start,
                      sources={str(s.relative_to(root)): hashlib.sha256(s.read_bytes()).hexdigest()
                               for s in sources})
        results.append(result)
        print(json.dumps(dict(test=name, passed=True, seconds=result['seconds'])), flush=True)
    (a.out / 'summary.json').write_text(json.dumps(dict(
        scope='RTL_UNIT_AND_BUS_MODEL_INTEGRATION_NOT_CNN_OR_BOARD', tests=results), indent=2)+'\n')


if __name__ == '__main__':
    main()
