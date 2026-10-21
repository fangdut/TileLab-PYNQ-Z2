"""Package the proven snapshot, never substitute the current experiment."""
from pathlib import Path
import argparse,json,hashlib,shutil,zipfile,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    for n in ['hardware','software','hls','profile','validation','verified','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];repo=root.parents[1]
    check=json.loads((a.verified/'verification.json').read_text(encoding='utf8'))
    if check['status']!='PHYSICAL_ALL_INTEGER_BENCHMARK_PASSED_NOT_REALTIME':raise ValueError('Unverified snapshot')
    if sha(a.profile/'model.bin')!=check['model_sha256'] or sha(a.hls/'src/texture_integer.cpp')!=check['hls_source_sha256']:raise ValueError('Frozen model/source mismatch')
    for key,file in [('bit_sha256',a.hardware/'system.bit'),('xsa_sha256',a.hardware/'system.xsa'),('elf_sha256',a.software/'texture_transport/build/texture_transport.elf')]:
        if sha(file)!=check['programmed_build'][key]:raise ValueError('Frozen compiled artifact mismatch')
    if a.out.exists():raise ValueError('Use a fresh package folder')
    a.out.mkdir(parents=True)
    def copy(source,dest):
        target=a.out/dest;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name in ['system.bit','system.xsa','implementation_status.json','timing_summary.rpt','utilization.rpt','clocks.rpt','drc.rpt']:
        copy(a.hardware/name,Path('hardware')/name)
    copy(a.hardware/'texture_v170.srcs/sources_1/bd/system/system.bd',Path('hardware/texture_v170.srcs/sources_1/bd/system/system.bd'))
    copy(a.software/'texture_transport/build/texture_transport.elf',Path('software/texture_transport/build/texture_transport.elf'))
    copy(a.software/'BUILD_RESULT.json',Path('software/BUILD_RESULT.json'))
    copy(a.hls/'solution/impl/export.zip',Path('hls/export.zip'))
    copy(a.hls/'solution/sim/report/texture_integer_cosim.rpt',Path('hls/texture_integer_cosim.rpt'))
    for name in ['texture_integer.cpp','test_integer.cpp']:
        copy(a.hls/'src'/name,Path('source/experimental/texture_v170/hls')/name)
    copy(a.software/'sources/main.c',Path('source/experimental/texture_v170/firmware/main.c'))
    for folder in ['scripts/texture_v170','tools/fpga_texture_v170']:
        for source in (root/folder).rglob('*'):
            if source.is_file() and source.suffix in ['.py','.tcl'] and '__pycache__' not in source.parts:copy(source,Path('source')/source.relative_to(root))
    # Pin the generator matching the actual test contract, not today's experiment.
    contracts={
        'fba67d8c9f3dc76ea6aed7255b82c21d10ba4b011632a68112fe13887f7fa04b':'68944eb',
        '05464440ca79e68d9d6ff6a77ed57b081002aa379eb922dcce35742af01cf8b6':'ea70ad4',
    }
    generator_commit=contracts.get(check['hls_source_sha256'])
    if not generator_commit:raise ValueError('No verified generator contract for this source')
    prefix='project/pynq_z2_tile_v1_53/'
    for relative in ['tools/fpga_texture_v170/make_vectors.py','tools/fpga_texture_v170/evaluate_lightweight.py','scripts/texture_v170/build_hls.tcl']:
        result=subprocess.run(['git','show',generator_commit+':'+prefix+relative],cwd=repo,check=True,capture_output=True)
        (a.out/'source'/relative).write_bytes(result.stdout)
    for source in a.hls.glob('test_*.bin'):copy(source,Path('unit_vectors')/source.name)
    for relative in ['scripts/ps7_preset.tcl','pynq_z2_tile_v1_53.sdk/ethernet_sources/safe_memcpy.c','pynq_z2_tile_v1_53.sdk/ethernet_sources/lscript.ld']:
        copy(root/relative,Path('source')/relative)
    for source in a.profile.iterdir():
        if source.is_file() and source.suffix in ['.bin','.json','.npz','.md','.npy']:copy(source,Path('model')/source.name)
    frozen_profile=root/'models/texture_v170_r1'
    for name in ['dataset_manifest.json','README.md']:
        if not (a.out/'model'/name).exists():copy(frozen_profile/name,Path('model')/name)
    copy(root/'tools/fpga_texture_v169/fetch_photos.py',Path('source/tools/fpga_texture_v170/fetch_photos.py'))
    for source in a.verified.iterdir():
        if source.is_file():copy(source,Path('reports')/source.name)
    with zipfile.ZipFile(a.out/'reports/all_117_board_raw.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for case in check['cases']:
            folder=a.validation/case['id']
            for name in ['raw_result.bin','scores.npy','evidence.json']:z.write(folder/name,case['id']+'/'+name)
    for ident in ['6621d769324f6e05d5838381','6621d769324f6e05d583835f']:
        for name in ['input.png','mask.png','overlay.png','evidence.json']:copy(a.validation/ident/name,Path('examples')/ident/name)
    for name in ['LICENSE','LICENSE_SCOPE.md','THIRD_PARTY_NOTICES.md']:copy(repo/name,Path(name))
    (a.out/'requirements_runtime.txt').write_text('numpy==2.5.2\nPillow==12.3.0\n')
    fps=check['autorestart_fixed_frame']['sustained_pl_fps']
    frames=check['autorestart_fixed_frame']['frames']
    (a.out/'README.md').write_text(f'''# V170 verified all-PL snapshot — not real-time acceptance

Pinned source: {a.hls.name}, matching timing-closed 100 MHz BIT/XSA/ELF. All 117 exposed historical MVTec Tile development images were physically processed on PYNQ-Z2; integer scores and original-size masks are exact. Image decisions: 84/84 anomalies (17/17 cracks), 0/33 normal false alarms. This is not independent or general-material accuracy. Crack segmentation remains coarse (historical mean IoU about 0.067).

Measured fixed-frame PL auto-restart: {fps:.6f} FPS, one ARM start followed by {frames} completed hardware frames. This is NOT continuous HDMI video and NOT the 10 FPS target. reports/verification.json binds source/model/build identities and all case hashes. all_117_board_raw.zip contains every raw hardware result and evidence file. Models and original photo URLs/SHA256 are recorded in model/; two original examples and actual overlays are included. unit_vectors/ contains the exact RTL input/reference files; the generator is pinned to local source commit {generator_commit}.

PL performs the complete integer detector. ARM performs transport, CRC, start/stop and timing; PC decodes files, sends RGB, renders masks and stores evidence. No CPU/GPU detection fallback. Runtime needs only Pillow/NumPy. Vitis/Vivado 2025.2 rebuild source is included. Programming is volatile JTAG; no Flash writes.

From this folder: python source/scripts/texture_v170/program_board.py --hardware hardware --software software --out runtime/program_new
Then: python source/tools/fpga_texture_v170/board_client.py --model model --image examples/6621d769324f6e05d583835f/input.png --out runtime/case_new
PC Ethernet: 192.168.33.30/24; board: 192.168.33.10:9136. Use new output folders. Decode/transport/display are the only PC runtime work.

Original code is MIT; MVTec-derived models/photos/evidence retain CC BY-NC-SA 4.0, and vendor IP/upstream weights retain original terms. This engineering snapshot is not a final competition submission.
''',encoding='utf8')
    files={p.relative_to(a.out).as_posix():sha(p) for p in a.out.rglob('*') if p.is_file()}
    (a.out/'PACKAGE_MANIFEST.json').write_text(json.dumps(files,indent=2))
    archive=a.out.with_suffix('.zip')
    if archive.exists():raise ValueError('Archive exists')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for source in a.out.rglob('*'):
            if source.is_file():z.write(source,source.relative_to(a.out))
    print(json.dumps(dict(path=str(archive),bytes=archive.stat().st_size,sha256=sha(archive))),flush=True)
if __name__=='__main__':main()
