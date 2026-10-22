"""Archive only a complete matching physical V179 run; never create acceptance."""
from pathlib import Path
import hashlib,json,shutil,sys
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
run=W/'v179_acceptance01';hw=W/'v179_hw01';dst=P/'reports/v179/verified_hdmi_overlap'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(P/'scripts/texture_v170'))
from verify_video import verify,verify_bus_skew_report
from verify_reset import verify as verify_reset
from verify_clock import verify as verify_clock
from verify_memory_layout import verify as verify_memory_layout
from video_layout import validate_frame_base
state=read(run/'progress.json');identity=read(run/'program/identity.json');hdmi=read(run/'hdmi117/summary.json');direct=read(run/'board117/summary.json');old=read(W/'v173_acceptance08/hdmi117/summary.json')
assert state['status']=='DEVELOPMENT_ACCURACY_PASS_SPEED_TARGET_PENDING'
assert read(W/'v179_physical_pipeline01.json')['status']=='EXPERIMENT_COMPLETE_REVIEW_ACTUAL_SPEED_BEFORE_PROMOTION'
assert direct['correct']==117 and direct['normal_false_alarms']==0 and direct['normal_images']==33
assert hdmi['normal_images']==33 and hdmi['anomalies_detected']==hdmi['anomalies']==84 and hdmi['cracks_detected']==hdmi['cracks']==17
assert hdmi['distinct_observed_photo_crcs']==117 and hdmi['arm_halt_checks']>=119
# The identical117-photo procedure determines its duration; a faster core also
# shortens the wait for three fresh completions. Report its actual duration.
assert hdmi['continuous_observation_seconds']>=180 and not hdmi['cpu_detection'] and not hdmi['gpu_detection']
assert hdmi['autonomous_hdmi_fps_over_photo_series']>old['autonomous_hdmi_fps_over_photo_series'], 'No accepted release without measured HDMI improvement'
clock_proof=verify_clock(hw)
assert sha(hw/'texture_integer_source.cpp')==sha(W/'v170_hls62/src/texture_integer.cpp')==read(W/'v179_all_c05/summary.json')['source_sha256']
assert hdmi['cases']==hdmi['correct']==direct['cases']==117 and not hdmi['normal_false_alarms'] and direct['all_integer_outputs_exact']
assert hdmi['both_arm_cores_halted'] and hdmi['cpu_per_frame_start_writes']==0
assert identity['build']['model_sha256']==read(W/'v173_acceptance08/program/identity.json')['build']['model_sha256']
assert verify(hw)['video'];verify_reset(hw);verify_bus_skew_report(hw/'bus_skew.rpt')
preflight=read(hw/'candidate_preflight.json');assert preflight['video_variant']=='overlap_v175'
memory_layout_proof=verify_memory_layout(hw,preflight['memory_layout'])
rtls={f.name:sha(f) for f in (hw/'rtl_snapshot').iterdir() if f.suffix in ('.v','.sv')}
assert rtls==preflight['video_rtl_sources']=={f.name:sha(f) for f in (P/'experimental/video_overlap_v175/rtl').iterdir() if f.suffix in ('.v','.sv')}
for role in ['bit','xsa']:
    assert sha(hw/('system.'+role))==identity['build'][role+'_sha256']
inputs={}
for case in ['identity_gray','good','crack']:
    evidence=read(run/(case+'_snapshot/evidence.json'))
    assert evidence['video_register_version']==0x17500001 and evidence['arm_cores_halted_during_dump'] and evidence['input_base_stable_during_snapshot']
    validate_frame_base(0x17500001,evidence['input_base'])
    assert evidence['files']['rgb.bin']==sha(run/(case+'_snapshot/rgb.bin'))
    inputs[case]={k:evidence[k] for k in ['input_base','rgb_crc32','capture_sequence','pl_sequence','pl_image_alarm']}
    if case!='identity_gray':assert read(run/(case+'_reference_audit/audit.json'))['all_values_exact']
assert inputs['good']['pl_image_alarm']==0 and inputs['crack']['pl_image_alarm']==1
dst.mkdir(parents=True,exist_ok=False)
def cp(src,name):
    target=dst/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
for name in ['timing_summary.rpt','utilization.rpt','implementation_status.json','video_cdc.rpt','bus_skew.rpt','candidate_preflight.json','drc.rpt','optimization_strategy.json','clocks.rpt']:
    cp(hw/name,Path('hardware')/name)
if (hw/'physical_repair.json').exists():cp(hw/'physical_repair.json',Path('hardware/physical_repair.json'))
for folder in sorted(hw.glob('physical_repair*')):
    if folder.is_dir():
        for f in folder.rglob('*'):
            if f.is_file() and f.name in ['implementation_status.json','timing_summary.rpt','canonical_header_alignment.json','physical_repair.json']:
                cp(f,Path('hardware')/folder.name/f.relative_to(folder))
for src,name in [('progress.json','iteration.json'),('program/identity.json','program_identity.json'),('board117/summary.json','direct117/summary.json'),('board117/plan.json','direct117/plan.json'),('board117/progress.json','direct117/results.json'),('board117/autorestart_benchmark.json','direct117/autorestart.json'),('hdmi117/summary.json','hdmi117/summary.json'),('hdmi117/results.json','hdmi117/results.json'),('hdmi117/plan.json','hdmi117/plan.json'),('hdmi117/experiment.log','hdmi117/experiment.log'),('hdmi117/experiment.tcl','hdmi117/experiment.tcl'),('color_profile.json','color_profile.json')]:cp(run/src,Path(name))
for case in ['identity_gray','good','crack']:
    for name in ['report.json','samples.json','control.log','control.tcl']:cp(run/(case+'_live')/name,Path(case)/'live'/name)
    for name in ['evidence.json','snapshot.log','snapshot.tcl','actual_hdmi_input.png','actual_pl_mask.png','actual_pl_overlay.png']:
        cp(run/(case+'_snapshot')/name,Path(case)/'snapshot'/name)
    if case!='identity_gray':cp(run/(case+'_reference_audit/audit.json'),Path(case)/'independent_reference_audit.json')
statuses={p.name:read(p) for p in (run/'hdmi117').glob('*_source.json')}
(dst/'hdmi117/source_statuses.json').write_text(json.dumps(statuses,indent=2)+'\n')
(dst/'hardware/rtl_snapshot_hashes.json').write_text(json.dumps(rtls,indent=2)+'\n')
proof=dict(scope='PHYSICAL_REAL_PHOTO_HDMI_DEVELOPMENT_ACCEPTANCE_NOT_FINAL_COMPETITION',video_variant='overlap_v175',
    boot_identity=identity['boot_identity'],model_sha256=identity['build']['model_sha256'],kernel_sha256=sha(hw/'texture_integer_source.cpp'),
    bit_sha256=identity['build']['bit_sha256'],xsa_sha256=identity['build']['xsa_sha256'],elf_sha256=identity['build']['elf_sha256'],
    threshold=10908,model_changed=False,threshold_changed=False,runtime_detection='FPGA only',arm_halt_checks=hdmi['arm_halt_checks'],
    cpu_per_frame_start_writes=0,cases=117,normal_false_alarms=0,normal_images=33,anomalies_detected=84,anomalies=84,cracks_detected=17,cracks=17,
    continuous_hdmi_fps=hdmi['autonomous_hdmi_fps_over_photo_series'],continuous_seconds=hdmi['continuous_observation_seconds'],
    continuous_frames=hdmi['autonomous_frames_in_interval'],fixed_frame_fps=direct['autorestart_fixed_frame_fps'],
    previous_v173_r2_hdmi_fps=old['autonomous_hdmi_fps_over_photo_series'],
    hdmi_fps_improvement_fraction=hdmi['autonomous_hdmi_fps_over_photo_series']/old['autonomous_hdmi_fps_over_photo_series']-1,
    physical_input_identity=inputs,benchmark_is_blind=False,ten_fps_passed=hdmi['autonomous_hdmi_fps_over_photo_series']>=10,competition_final_acceptance=False,clock_proof=clock_proof,memory_layout_proof=memory_layout_proof,
    local_readable_report=str(run/'report.html'),report_sha256=sha(run/'report.html'),source_status_read_retries=hdmi['source_status_read_retries'])
if (W/'v179_transport_stress01/report.json').exists():
    stress=read(W/'v179_transport_stress01/report.json')
    assert stress['status']=='PASS' and stress['completed']==300 and stress['boot_identity']==identity['boot_identity']
    for src,name in [('v179_transport_stress01/report.json','post_video_transport/report.json'),('resume_transport_after_v179_video.log','post_video_transport/resume.log'),('resume_transport_after_v179_video.tcl','post_video_transport/resume.tcl')]:cp(W/src,Path(name))
    proof.update(post_video_transport_queries=300,post_video_transport_stress_passed=True,arm_cores_resumed_only_after_stopped_video_for_transport_test=True)
proof['files']={p.relative_to(dst).as_posix():sha(p) for p in dst.rglob('*') if p.is_file()}
(dst/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k!='files'}),flush=True)
