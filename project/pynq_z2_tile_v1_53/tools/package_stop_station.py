"""Rebuild a portable workstation bundle from this repository, without EDA."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--zip',type=Path)
    p.add_argument('--transport',type=Path,help='Optional separately verified transport firmware workspace')
    p.add_argument('--transport-proof',type=Path)
    a=p.parse_args()
    if bool(a.transport)!=bool(a.transport_proof):p.error('--transport and --transport-proof are required together')
    project=Path(__file__).resolve().parents[1]
    repo=Path(__file__).resolve().parents[3]
    baseline=repo/'deliverables/V179_Verified_HDMI_8p17FPS_Dev.zip'
    digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    if digest(baseline)!='41305dd8d66505f979870d9977c4bccbca974b5d1a1516907e9c44ca05da0ed7':
        raise ValueError('Verified baseline archive differs')
    out=a.out.resolve()
    if out.is_relative_to(project):
        raise ValueError('Output must be outside the source project')
    out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(baseline) as archive:
        if archive.testzip() is not None:raise ValueError('Corrupt baseline archive')
        for name in archive.namelist():
            dest=(out/'verified_hdmi'/name).resolve()
            if not dest.is_relative_to((out/'verified_hdmi').resolve()):
                raise ValueError('Unsafe archive path')
            if name.endswith('/'):dest.mkdir(parents=True,exist_ok=True)
            else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(archive.read(name))
    reports=['reports/v193']+[f'reports/{v}' for v in ['v194','v195'] if (project/f'reports/{v}').exists()]
    for rel in ['host/stop_inspect_station','data/stop_inspect_demo','skill','scripts/texture_v170','tools/fpga_texture_v170']+reports:
        shutil.copytree(project/rel,out/'project'/rel,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc','runtime'))
    for name in ['LICENSE','LICENSE_SCOPE.md','THIRD_PARTY_NOTICES.md']:
        shutil.copy2(repo/name,out/name)
    if a.transport:
        proof=json.loads(a.transport_proof.read_text())
        candidate=json.loads((a.transport/'BUILD_RESULT.json').read_text())
        original=json.loads((out/'verified_hdmi/software/BUILD_RESULT.json').read_text())
        if not proof.get('transport_validated') or proof['elf_sha256']!=candidate['elf_sha256']:
            raise ValueError('Transport lacks matching physical validation')
        for key in ['bit_sha256','xsa_sha256','model_sha256']:
            if candidate[key]!=original[key]:raise ValueError('Transport changed accepted detector: '+key)
        elf=a.transport/'texture_transport/build/texture_transport.elf'
        if digest(elf)!=candidate['elf_sha256']:raise ValueError('Transport ELF differs')
        shutil.copy2(elf,out/'verified_hdmi/software/texture_transport/build/texture_transport.elf')
        shutil.copy2(a.transport/'BUILD_RESULT.json',out/'verified_hdmi/software/BUILD_RESULT.json')
        firmware=out/'verified_hdmi/source/experimental/texture_v170/firmware'
        for name in ['main.c','transport_crc32.h']:
            source=a.transport/'sources'/name
            if digest(source)!=candidate['sources'][name]:raise ValueError('Transport source differs: '+name)
            shutil.copy2(source,firmware/name)
        shutil.copy2(a.transport_proof,out/'verified_hdmi/software/transport_validation.json')
    shutil.copy2(project/'host/stop_inspect_station/start_station.ps1',out/'start_station.ps1')
    shutil.copy2(project/'host/stop_inspect_station/start_station.cmd',out/'启动检测.cmd')
    if (project/'tools/fetch_external_v194.py').exists():
        shutil.copy2(project/'tools/fetch_external_v194.py',out/'project/tools/fetch_external_v194.py')
    if (project/'tools/fetch_reference_v195.py').exists():
        shutil.copy2(project/'tools/fetch_reference_v195.py',out/'project/tools/fetch_reference_v195.py')
    (out/'requirements.txt').write_text('numpy>=1.26,<3\nPillow>=10,<13\n')
    (out/'README.md').write_text('''# TileLab stopped-input FPGA workstation

Windows, Python3.12, NumPy/Pillow, Vivado/Vitis2025.2 and board USB drivers are required.

1. python -m pip install -r requirements.txt
2. python project/skill/verify_files.py .
3. python project/host/stop_inspect_station/deploy_workstation.py --bundle . --out runtime/run01
4. python project/host/stop_inspect_station/server.py --config runtime/run01/station_config.json
5. Open http://127.0.0.1:8793/ .

XSDB defaults to D:/2025.2/Vitis/bin/xsdb.bat; set TILELAB_XSDB for another path. Deployment is volatile only. The old station/source must be closed before programming.

See project/host/stop_inspect_station/README.md and project/reports/v193/status.html for workflow, evidence and limits. Inference is physical FPGA PL. The PC manages input, transport, display and operator confirmation. There is no physical conveyor or actuator in this demonstrator. Bundled photos are an exposed development set, not blind accuracy validation. Original code MIT; MVTec photos/derived model/evidence CC BY-NC-SA4.0; vendor/upstream terms preserved.

V195 offline reference-calibration tools/evidence are included when present. They do not change the live baseline or qualify arbitrary imports for release. See project/reports/v195/status.html and project/tools/fpga_texture_v170/REFERENCE_CALIBRATION.md. Offline fitting additionally needs the PyTorch/torchvision versions recorded in that report; these are not runtime detector dependencies.
''',encoding='utf8')
    files={f.relative_to(out).as_posix():dict(bytes=f.stat().st_size,sha256=digest(f))
           for f in sorted(out.rglob('*')) if f.is_file()}
    (out/'manifest.json').write_text(json.dumps(dict(files=files),indent=2))
    if a.zip:
        if a.zip.exists():raise ValueError('Archive output already exists')
        a.zip.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for f in sorted(out.rglob('*')):
                if f.is_file():archive.write(f,out.name+'/'+f.relative_to(out).as_posix())
        print(json.dumps(dict(archive=str(a.zip.resolve()),sha256=digest(a.zip))))
    print(json.dumps(dict(bundle=str(out),files=len(files))))


if __name__=='__main__':main()
