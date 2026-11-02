"""Resume implementation after process interruption, preserving prior logs.

Only an unexported video candidate with complete synthesis is eligible.
Uses its saved build script and repeats every timing/DRC/Gray-bus export gate.
Does not program the board.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, shutil
from build_candidate import preflight

def main():
    p=argparse.ArgumentParser()
    for n in ['hardware','hls','regression','profile']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=a.hardware
    if any((out/n).exists() for n in ['system.bit','system.xsa','implementation_status.json','candidate_preflight.json']):
        raise ValueError('Only an interrupted, unexported candidate may resume')
    proof=preflight(a.hls,a.regression,a.profile)
    if (out/'texture_integer_source.cpp').read_bytes()!=(a.hls/'src/texture_integer.cpp').read_bytes():
        raise ValueError('Saved hardware and verified HLS source differ')
    archive=out/'interrupted_implementation01'
    if archive.exists():raise ValueError('Interruption archive exists; inspect before another attempt')
    shutil.copytree(out/'texture_v170.runs/impl_1',archive)
    original=out.with_name(out.name+'_console.log')
    shutil.copy2(original,archive/'parent_console.log')
    build=(out/'build_hardware_source.tcl').read_text()
    marker='set_property STEPS.OPT_DESIGN.ARGS.DIRECTIVE $opt_directive [get_runs impl_1]'
    if build.count(marker)!=1:raise ValueError('Saved build export section is ambiguous')
    strategy=json.loads((out/'optimization_strategy.json').read_text())
    script=out/'resume_implementation01.tcl'
    script.write_text('set out {'+out.as_posix()+'}\nset video 1\nset jobs 1\n'
        +'set opt_directive '+strategy['opt_directive']+'\nset_param general.maxThreads 4\n'
        +'open_project $out/texture_v170.xpr\n'
        +'if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Completed synthesis required"}\n'
        +'reset_run impl_1\n'+marker+build.split(marker)[1])
    evidence=dict(scope='RESUME_INTERRUPTED_IMPLEMENTATION_NOT_PROGRAMMED',
        source_sha256=proof['source_sha256'],saved_build_sha256=hashlib.sha256((out/'build_hardware_source.tcl').read_bytes()).hexdigest(),
        resume_script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),archive=str(archive))
    (out/'interruption_resume.json').write_text(json.dumps(evidence,indent=2)+'\n')
    with original.open('a') as log:
        log.write('\nRESUMING_INTERRUPTED_IMPLEMENTATION_FROM_COMPLETED_SYNTHESIS\n');log.flush()
        run=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(script),'-notrace','-nolog','-nojournal'],stdout=log,stderr=subprocess.STDOUT)
    proof.update(strategy)
    (out/'candidate_preflight.json').write_text(json.dumps(proof,indent=2)+'\n')
    if run.returncode:raise RuntimeError('Resumed implementation failed; original and resumed logs preserved')
    status=json.loads((out/'implementation_status.json').read_text())
    if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors']:
        raise RuntimeError('Physical timing/DRC rejected')
    print(json.dumps(dict(scope='TIMING_CLOSED_NOT_PROGRAMMED',**status)),flush=True)

if __name__=='__main__':main()
