"""Package matching initial PL migration evidence; not a competition submission."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    for name in ('hardware','software','hls','model','examples','validation','report','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];repo=root.parents[1]
    accepted=json.loads((a.report/'acceptance.json').read_text(encoding='utf8'))
    if accepted['status']!='INITIAL_FULL_PL_MIGRATION_PASSED':raise ValueError('Initial migration has not passed')
    if a.out.exists():raise ValueError('Use a new release folder')
    a.out.mkdir(parents=True)
    def copy(src,dest):
        dest=a.out/dest;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    for name in ('system.bit','system.xsa','implementation_status.json','timing_summary.rpt','utilization.rpt','clocks.rpt','drc.rpt'):copy(a.hardware/name,Path('hardware')/name)
    copy(a.hardware/'texture_v169.srcs/sources_1/bd/system/system.bd',Path('hardware/texture_v169.srcs/sources_1/bd/system/system.bd'))
    copy(a.software/'texture_transport/build/texture_transport.elf',Path('software/texture_transport/build/texture_transport.elf'))
    copy(a.software/'BUILD_RESULT.json',Path('software/BUILD_RESULT.json'))
    copy(a.hls/'solution/impl/export.zip',Path('hls/export.zip'))
    copy(a.hls/'solution/sim/report/texture_infer_cosim.rpt',Path('hls/texture_infer_cosim.rpt'))
    copy(a.hls/'src/texture_infer.cpp',Path('hls/texture_infer_source.cpp'))
    for folder in ('experimental/texture_v169','scripts/texture_v169','tools/fpga_texture_v169','models/texture_v169_r1'):
        for src in (root/folder).rglob('*'):
            if src.is_file() and '__pycache__' not in src.parts and src.suffix in ('.py','.cpp','.c','.tcl','.md','.json','.npz','.npy'):copy(src,Path('source')/src.relative_to(root))
    for relative in ('scripts/ps7_preset.tcl','pynq_z2_tile_v1_53.sdk/ethernet_sources/safe_memcpy.c','pynq_z2_tile_v1_53.sdk/ethernet_sources/lscript.ld'):copy(root/relative,Path('source')/relative)
    for name in ('LICENSE','LICENSE_SCOPE.md','THIRD_PARTY_NOTICES.md'):copy(repo/name,Path(name))
    for name in ('model.bin','graph.json','compression.npz','model.json','fit_protocol.json','normal_calibration.json','summary.json','results.json'):copy(a.model/name,Path('model')/name)
    for check in accepted['cases']:
        name=check['id']+'_scores.npy';copy(a.model/name,Path('model')/name)
    for source,destination in ((a.examples,'examples'),(a.validation,'board_evidence'),(a.report,'reports')):
        for src in source.rglob('*'):
            if src.is_file():copy(src,Path(destination)/src.relative_to(source))
    (a.out/'requirements_runtime.txt').write_text('numpy==2.5.2\nPillow==12.3.0\n')
    (a.out/'start_station.ps1').write_text('''param([string]$Python='python')
$ErrorActionPreference='Stop'
& $Python -X utf8 "$PSScriptRoot/source/tools/fpga_texture_v169/station.py" --dataset "$PSScriptRoot/examples" --model "$PSScriptRoot/model" --out "$PSScriptRoot/runtime/records" --port 8789
''')
    (a.out/'README.md').write_text('''# V169 full-PL migration check

This is an initial real-photo FPGA migration package, not final competition acceptance. Two normal/crack board cases are recorded in reports/acceptance.json. Historical 116/117 accuracy is an offline exposed benchmark, not a 117-image board measurement. Arbitrary painted/mixed materials, walls and real-time performance are unvalidated.

PL performs resize, normalization, the complete feature CNN, pooling, PCA, nearest-normal search, smoothing, image alarm and original-size mask. ARM performs transport/control/CRC. PC performs file decoding, transport and display. There is no CPU/GPU detection fallback.

Use Vitis/Vivado 2025.2 at D:/2025.2 and Python with requirements_runtime.txt. Program the matching image using source/scripts/texture_v169/program_board.py --hardware hardware --software software --out runtime/program_new (choose a new output folder). PC Ethernet is 192.168.33.30/24; board is 192.168.33.10:9135. Run start_station.ps1 or the equivalent station.py command. The initial 100 MB model upload occurs once per boot. Model.bin is included; Torch is unnecessary for runtime.

Source rebuild instructions: source/experimental/texture_v169/README.md. Images are unedited MVTec AD Tile photos; examples/manifest.json records sources and SHA256. MVTec-derived data retain CC BY-NC-SA 4.0. Original code is MIT; vendor code and upstream pretrained weights retain their original terms.
''',encoding='utf8')
    files={p.relative_to(a.out).as_posix():sha(p) for p in a.out.rglob('*') if p.is_file()}
    (a.out/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(scope=accepted['status'],files=files),indent=2))
    archive=a.out.with_suffix('.zip')
    if archive.exists():raise ValueError('Archive already exists')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in a.out.rglob('*'):
            if path.is_file():z.write(path,path.relative_to(a.out))
    # Small compiled runtime for GitHub; the exact model is reconstructed from
    # the frozen profile with rebuild_model.py or copied from this full package.
    small=a.out.parent/(a.out.name+'_compiled.zip')
    if small.exists():raise ValueError('Compiled archive already exists')
    with zipfile.ZipFile(small,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('hardware','software','hls'):
            for path in (a.out/folder).rglob('*'):
                if path.is_file():z.write(path,path.relative_to(a.out))
    record=dict(full_package=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),compiled_package=str(small),compiled_bytes=small.stat().st_size,compiled_sha256=sha(small))
    (a.out.parent/(a.out.name+'_package.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
if __name__=='__main__':main()
