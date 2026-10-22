"""Freeze checked video artifacts and evidence; never competition acceptance."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zipfile
from verify_reset import verify
from verify_video import verify as verify_video,verify_bus_skew_report

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for n in ['hardware','run','hls','profile','player','evidence','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--source-commit',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[2];repo=root.parents[1]
    if not re.fullmatch('[0-9a-f]{40}',a.source_commit):raise ValueError('Pinned source commit required')
    archive=a.out.with_suffix('.zip')
    if a.out.exists() or archive.exists():raise ValueError('Fresh package and archive required')
    read=lambda p:json.loads(p.read_text())
    hdmi=read(a.run/'hdmi117/summary.json');direct=read(a.run/'board117/summary.json')
    state=read(a.run/'progress.json');identity=read(a.run/'program/identity.json')
    software=a.run/'software.sdk';build=read(software/'BUILD_RESULT.json')
    if state['status']!='DEVELOPMENT_ACCURACY_PASS_SPEED_TARGET_PENDING':raise ValueError('Completed physical development experiment required')
    if hdmi['cases']!=117 or hdmi['correct']!=117 or hdmi['normal_false_alarms'] or not hdmi['both_arm_cores_halted'] or hdmi['cpu_per_frame_start_writes']:
        raise ValueError('Physical HDMI accuracy/ownership proof failed')
    if direct['cases']!=117 or not direct['all_integer_outputs_exact']:raise ValueError('Full direct numerical regression required')
    verify(a.hardware);verify_video(a.hardware);verify_bus_skew_report(a.hardware/'bus_skew.rpt')
    status=read(a.hardware/'implementation_status.json')
    if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors']:raise ValueError('Physical timing/DRC failed')
    source=a.hls/'src/texture_integer.cpp'
    if source.read_bytes()!=(a.hardware/'texture_integer_source.cpp').read_bytes():raise ValueError('Hardware/HLS source mismatch')
    for kind,path in [('bit',a.hardware/'system.bit'),('xsa',a.hardware/'system.xsa'),('elf',software/'texture_transport/build/texture_transport.elf')]:
        if sha(path)!=build[kind+'_sha256'] or build[kind+'_sha256']!=identity['build'][kind+'_sha256']:raise ValueError('Artifact identity mismatch: '+kind)
    if sha(a.profile/'model.bin')!=identity['build']['model_sha256']:raise ValueError('Frozen model mismatch')
    with zipfile.ZipFile(a.hardware/'system.xsa') as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or z.read(bits[0])!=(a.hardware/'system.bit').read_bytes():raise ValueError('Whole BIT/XSA identity mismatch')
    for case in ['good','crack']:
        if not read(a.run/(case+'_reference_audit/audit.json'))['all_values_exact']:raise ValueError('Saved physical input audit failed')
    verified=read(a.evidence/'verification.json')
    if verified['boot_identity']!=identity['boot_identity'] or verified['bit_sha256']!=build['bit_sha256']:
        raise ValueError('Archived physical evidence belongs to another boot/build')
    for n,digest in verified['files'].items():
        f=a.evidence/n
        if not f.resolve().is_relative_to(a.evidence.resolve()) or sha(f)!=digest:raise ValueError('Archived evidence hash mismatch: '+n)
    a.out.mkdir(parents=True)
    def cp(src,dst):
        dst=a.out/dst;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    for n in ['system.bit','system.xsa','implementation_status.json','timing_summary.rpt','utilization.rpt','video_cdc.rpt','bus_skew.rpt','physical_repair.json','drc.rpt']:
        cp(a.hardware/n,Path('hardware')/n)
    cp(a.hardware/'texture_v170.srcs/sources_1/bd/system/system.bd',Path('hardware/texture_v170.srcs/sources_1/bd/system/system.bd'))
    cp(software/'BUILD_RESULT.json',Path('software/BUILD_RESULT.json'))
    cp(software/'texture_transport/build/texture_transport.elf',Path('software/texture_transport/build/texture_transport.elf'))
    cp(source,Path('source/texture_integer.cpp'));cp(source,Path('source/experimental/texture_v170/hls/frozen')/(a.hls.name+'.cpp'))
    cp(a.hls/'src/test_integer.cpp',Path('source/experimental/texture_v170/hls/test_integer.cpp'))
    cp(a.hls/'solution/impl/export.zip',Path('hls/accepted_export.zip'))
    cp(a.hls/'solution/sim/report/texture_integer_cosim.rpt',Path('hls/rtl_cosim.rpt'))
    for n in ['test_model.bin','test_rgb.bin','test_expected.bin','test_fa_expected.bin','test_fb_expected.bin']:cp(a.hls/n,Path('unit_vectors')/n)
    for n in ['model.bin','graph.json']:cp(a.profile/n,Path('model')/n)
    for folder in ['scripts/texture_v170','tools/fpga_texture_v170','experimental/video_v171/source','experimental/texture_v170/firmware']:
        for f in (root/folder).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix in ['.py','.tcl','.c','.h','.md','.cs','.ps1']:cp(f,Path('source')/f.relative_to(root))
    for f in (a.hardware/'rtl_snapshot').iterdir():
        if f.is_file():cp(f,Path('source/experimental/video_v171/rtl')/f.name)
    cp(root/'scripts/ps7_preset.tcl',Path('source/scripts/ps7_preset.tcl'))
    cp(root/'experimental/packed_mac_v173/build_detector_hls.tcl',Path('source/experimental/packed_mac_v173/build_detector_hls.tcl'))
    for n in ['LICENSE','LICENSE_SCOPE.md','THIRD_PARTY_NOTICES.md']:cp(repo/n,Path(n))
    cp(a.player,Path('source/RealPhotoSource.exe'))
    for f in a.evidence.rglob('*'):
        if f.is_file():cp(f,Path('evidence/verified')/f.relative_to(a.evidence))
    for n in ['progress.json','color_profile.json','program/identity.json','board117/summary.json','board117/autorestart_benchmark.json','hdmi117/summary.json','hdmi117/results.json','hdmi117/plan.json','hdmi117/experiment.log']:
        cp(a.run/n,Path(n))
    for case in ['identity_gray','good','crack']:
        for f in (a.run/(case+'_snapshot')).iterdir():
            if f.suffix in ['.png','.json','.log','.tcl','.bin']:cp(f,Path(case+'_snapshot')/f.name)
        if case!='identity_gray':cp(a.run/(case+'_reference_audit/audit.json'),Path(case+'_reference_audit/audit.json'))
    raw=a.out/'evidence/all117_direct_raw.zip';raw.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(raw,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        files=list((a.run/'board117').rglob('raw_result.bin'))
        if len(files)!=117:raise ValueError('All 117 raw board outputs required')
        for f in files:
            z.write(f,f.relative_to(a.run/'board117'))
            evidence=f.with_name('evidence.json');z.write(evidence,evidence.relative_to(a.run/'board117'))
    report=(a.run/'report.html').read_text();photos=read(a.run/'hdmi117/plan.json')['photos']
    for ident in ['6621d769324f6e05d5838381','6621d769324f6e05d583835f']:
        row=next(r for r in photos if r['id']==ident);f=Path(row['file'])
        if sha(f)!=row['sha256']:raise ValueError('Original photo SHA mismatch')
        dst=Path('originals')/f.name;cp(f,dst);report=report.replace(f.as_uri(),dst.as_posix())
    (a.out/'report.html').write_text(report,encoding='utf8')
    fps=hdmi['autonomous_hdmi_fps_over_photo_series']
    (a.out/'README.md').write_text(f'''# Verified FPGA video development snapshot

Actual HDMI input: 117/117 exposed MVTec Tile development photos correct, 0/33 normal false alarms, 84/84 anomalies and 17/17 cracks detected. FPGA completed {hdmi['autonomous_frames_in_interval']} autonomous detections over {hdmi['continuous_observation_seconds']} seconds ({fps:.6f} FPS). Both ARM cores were checked halted {hdmi['arm_halt_checks']} times; no CPU/GPU detection or CPU per-frame start writes. Fixed-frame speed: {direct['autorestart_fixed_frame_fps']:.6f} FPS.

This is not a final competition submission. Independent blind accuracy, arbitrary painted/mixed materials, precise crack tracing and sustained 10 FPS remain open. Input photos are original publicly sourced MVTec photographs, displayed through HDMI; this is not evidence of a new camera or a complete physical tile installation.

Open report.html. hardware/ contains the exact programmed BIT/XSA; software/ the matching transport ELF; model/ the frozen model. evidence/all117_direct_raw.zip preserves every full board output. Source/model/artifact hashes are in PACKAGE_MANIFEST.json. The recorded boot {identity['boot_identity']} belongs to this experiment; reruns need fresh programming and validation records.

Full project and vendor IP dependencies: https://github.com/fangdut/TileLab-PYNQ-Z2/tree/{a.source_commit} . The exact accepted HLS source is source/texture_integer.cpp; hls/accepted_export.zip and unit_vectors/ match it. Later experimental kernels in the repository are separate. Rebuilding the complete Vivado project requires that pinned repository and AMD tools 2025.2; this archive contains compiled artifacts and supporting sources.

From the extracted package root, volatile JTAG programming is supported with:
python source/scripts/texture_v170/program_board.py --hardware hardware --software software --out runtime/program_new

Use a fresh output folder. PC Ethernet: 192.168.33.30/24; board: 192.168.33.10:9136. Runtime file transport uses numpy/Pillow; Torch is only needed for optional offline reference audits. HDMI inference and color correction run in PL. Recalibrate from an independent gray ramp after changing the HDMI source color settings; archived color_profile.json records this experiment only. No Flash programming is performed.

Original code is MIT. MVTec-derived photos/models/evidence retain CC BY-NC-SA 4.0; AMD/Xilinx/Digilent and other upstream components retain their licenses.
''',encoding='utf8')
    manifest=dict(scope='VERIFIED_DEVELOPMENT_VIDEO_SNAPSHOT_NOT_FINAL_COMPETITION',source_commit=a.source_commit,
        hls_source_sha256=sha(source),boot_identity=identity['boot_identity'],build=build,
        continuous_hdmi=hdmi,files={f.relative_to(a.out).as_posix():sha(f) for f in a.out.rglob('*') if f.is_file()})
    (a.out/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in a.out.rglob('*'):
            if f.is_file():z.write(f,f.relative_to(a.out))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Package CRC validation failed')
        for n,digest in manifest['files'].items():
            if hashlib.sha256(z.read(n)).hexdigest()!=digest:raise ValueError('Packaged SHA mismatch: '+n)
    print(json.dumps(dict(package=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),source_commit=a.source_commit)),flush=True)

if __name__=='__main__':main()
