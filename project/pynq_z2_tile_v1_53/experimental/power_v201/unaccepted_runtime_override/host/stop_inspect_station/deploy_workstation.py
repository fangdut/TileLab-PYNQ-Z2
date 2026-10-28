"""Deploy the matched stable baseline, then prepare a fresh station config."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--board', default='192.168.33.10')
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    bundle = a.bundle.resolve()
    sys.path.insert(0,str(bundle/'project/skill'))
    from verify_files import verify
    proof = verify(bundle)
    print(json.dumps(proof),flush=True)
    hardware = bundle/'verified_hdmi/hardware'
    software = bundle/'verified_hdmi/software'
    profile = bundle/'verified_hdmi/model'
    # Check the same artifact and timing contracts as the actual programmer,
    # before any board operation or runtime output is created.
    import hashlib
    build = json.loads((software/'BUILD_RESULT.json').read_text())
    scripts = bundle/'project/scripts/texture_v170'
    sys.path.insert(0, str(scripts))
    from verify_reset import verify as verify_reset
    from verify_clock import verify as verify_clock
    verify_reset(hardware)
    verify_clock(hardware)
    physical = json.loads((hardware/'implementation_status.json').read_text())
    if physical['setup_slack_ns'] < 0 or physical['hold_slack_ns'] < 0 or physical['drc_errors']:
        raise ValueError('Unaccepted physical implementation')
    for name, file in [('bit',hardware/'system.bit'),('xsa',hardware/'system.xsa'),
                       ('elf',software/'texture_transport/build/texture_transport.elf'),('model',profile/'model.bin')]:
        if hashlib.sha256(file.read_bytes()).hexdigest()!=build[name+'_sha256']:
            raise ValueError('Deployment pairing failed: '+name)
    operating_file=bundle/'operating_mode.json';operating=None
    if operating_file.is_file():
        operating=json.loads(operating_file.read_text(encoding='utf8'))
        if operating.get('schema')!=201 or operating.get('runtime_pl_clock_mhz')!=50 or operating.get('static_implementation_pl_clock_mhz')!=100 or physical['pl_clock_mhz']!=100:
            raise ValueError('Unsupported runtime clock mode')
    if a.verify_only:
        print('OFFLINE_DEPLOYMENT_GUARDS_PASS_NO_BOARD_OPERATION',flush=True)
        return
    out = a.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    program = out/'program'
    with (out/'program_console.log').open('w') as log:
        command=[sys.executable,'-X','utf8',str(scripts/'program_board.py'),
                        '--hardware',str(hardware),'--software',str(software),'--out',str(program)]
        if operating:command+=['--runtime-pl-clock-mhz',str(operating['runtime_pl_clock_mhz'])]
        subprocess.run(command,
                       check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    sys.path.insert(0,str(bundle/'project/tools/fpga_texture_v170'))
    from board_client import Board
    board = Board(a.board)
    identity = json.loads((program/'identity.json').read_text())
    if operating and identity.get('runtime_clock',{}).get('pl_clock_mhz')!=operating['runtime_pl_clock_mhz']:raise ValueError('Runtime clock proof missing')
    header,_,_=board.request(1)
    if header[8]!=identity['boot_identity']:
        raise ValueError('Network board differs from programmed board')
    board.upload(profile)
    config = dict(board=a.board,port=8793,
        hardware=os.path.relpath(hardware,out),program='program',
        profile=os.path.relpath(profile,out),
        catalog=os.path.relpath(bundle/'project/data/stop_inspect_demo/catalog.json',out),store='station_records')
    if (bundle/'profiles/index.json').is_file():
        config['profiles_registry']=os.path.relpath(bundle/'profiles/index.json',out)
    file = out/'station_config.json'
    file.write_text(json.dumps(config,indent=2),encoding='utf8')
    print('CONFIG '+str(file),flush=True)
    print('Volatile download and model load completed. Launch server.py with --config above.',flush=True)


if __name__=='__main__':
    main()
