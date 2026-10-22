"""One fresh source-bound hardware trial; no implicit promotion or Flash writes."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
from build_candidate import preflight
from verify_clock import verify as verify_clock

def review_board_result(run):
    """A successful subprocess alone is insufficient: inspect physical results."""
    run=Path(run);read=lambda p:json.loads(p.read_text())
    state=read(run/'progress.json');direct=read(run/'board117/summary.json');hdmi=read(run/'hdmi117/summary.json')
    if state['status']!='DEVELOPMENT_ACCURACY_PASS_SPEED_TARGET_PENDING':raise ValueError('Board accuracy stage did not pass')
    if direct['cases']!=117 or direct['correct']!=117 or not direct['all_integer_outputs_exact']:raise ValueError('Direct117 numerical/accuracy failure')
    for summary in [direct,hdmi]:
        if summary['cases']!=117 or summary['correct']!=117 or summary['normal_images']!=33 or summary['normal_false_alarms']!=0 or summary['anomalies_detected']!=84 or summary['anomalies']!=84 or summary['cracks_detected']!=17:
            raise ValueError('Physical photo classification regression')
        if summary['cpu_detection'] or summary['gpu_detection']:raise ValueError('Physical run used host inference')
    if not hdmi['both_arm_cores_halted'] or hdmi['arm_halt_checks']<119 or hdmi['cpu_per_frame_start_writes']!=0:raise ValueError('Autonomous PL runtime proof incomplete')
    if hdmi['distinct_observed_photo_crcs']!=117 or hdmi['continuous_observation_seconds']<180:raise ValueError('Full source-bound continuous photo series incomplete')
    rate=hdmi['autonomous_frames_in_interval']/hdmi['continuous_observation_seconds']
    if abs(rate-hdmi['autonomous_hdmi_fps_over_photo_series'])>1e-9:raise ValueError('Continuous FPS disagrees with measured counters/time')
    return dict(scope='PHYSICAL_RESULT_REVIEW_NOT_RELEASE_PROMOTION',fixed_frame_fps=direct['autorestart_fixed_frame_fps'],
                continuous_hdmi_fps=rate,continuous_seconds=hdmi['continuous_observation_seconds'],
                ten_fps_over_complete_series=rate>=10,benchmark_is_blind=False,competition_final_acceptance=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['hls','regression','profile','dataset','catalog','player','hardware','run','journal']:
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--video-rtl-gate',type=Path,required=True)
    p.add_argument('--clock-mhz',type=int,choices=[100,125],required=True)
    p.add_argument('--memory-layout',choices=['shared','split'],default='shared')
    p.add_argument('--ip-cache',type=Path)
    p.add_argument('--label',required=True)
    p.add_argument('--render-baseline',type=Path,required=True)
    p.add_argument('--render-previous',type=Path,required=True)
    p.add_argument('--max-repair-deficit-ns',type=float,default=.5)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];scripts=root/'scripts/texture_v170'
    if any(x.exists() for x in [a.hardware,a.run,a.journal]):raise ValueError('Fresh hardware/run/journal paths required')
    j=dict(scope='GUARDED_SOURCE_BOUND_PHYSICAL_TRIAL_NOT_FINAL_ACCEPTANCE',status='PREFLIGHT',stages=[],
           requested_pl_clock_mhz=a.clock_mhz,memory_layout=a.memory_layout,hls=str(a.hls),regression=str(a.regression),flash_written=False)
    def save():
        j['board_programmed']=(a.run/'program/identity.json').exists()
        a.journal.write_text(json.dumps(j,indent=2)+'\n')
    def run(name,args,timeout,env=None):
        j['status']=name;save();started=time.monotonic()
        print(json.dumps(dict(stage=name,state='started')),flush=True)
        log=a.journal.with_name(a.journal.stem+'_'+name+'.log')
        with log.open('w') as f:
            r=subprocess.run([str(x) for x in args],cwd=root,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout)
        j['stages'].append(dict(stage=name,returncode=r.returncode,seconds=time.monotonic()-started,log=str(log)));save()
        return r.returncode
    try:
        save();j['numerical_preflight']=preflight(a.hls,a.regression,a.profile);save()
        env=os.environ.copy()
        if a.ip_cache:env['TILE_TEXTURE_IP_CACHE']=str(a.ip_cache)
        else:env.pop('TILE_TEXTURE_IP_CACHE',None)
        code=run('hardware',[sys.executable,'-X','utf8',scripts/'build_candidate.py',
            '--hls',a.hls,'--regression',a.regression,'--profile',a.profile,'--out',a.hardware,
            '--video','--video-variant','overlap_v175','--video-rtl-gate',a.video_rtl_gate,
            '--clock-mhz',a.clock_mhz,'--opt-directive','Default','--memory-layout',a.memory_layout],5400,env)
        if code:
            file=a.hardware/'implementation_status.json'
            if not file.exists():raise RuntimeError('Build failed before physical reports; no programming')
            status=json.loads(file.read_text())
            if status['drc_errors'] or status['dsp']>220:raise RuntimeError('Physical DRC/capacity failed; no programming')
            if status['setup_slack_ns']>=0 and status['hold_slack_ns']>=0:raise RuntimeError('Export failed independently of timing; inspect log')
            if status['setup_slack_ns'] < -a.max_repair_deficit_ns:
                raise RuntimeError('Timing deficit requires another logic change; repeated placement deferred')
            if run('single_timing_repair',[sys.executable,'-X','utf8',scripts/'repair_physical.py',
                '--hardware',a.hardware,'--out',a.hardware/'physical_repair01'],3600):
                raise RuntimeError('One physical repair failed; no programming')
        verify_clock(a.hardware)
        from verify_memory_layout import verify as verify_memory_layout
        j['memory_layout_proof']=verify_memory_layout(a.hardware,a.memory_layout);save()
        if run('board',[sys.executable,'-X','utf8',scripts/'accept_video_candidate.py',
            '--hardware',a.hardware,'--hls',a.hls,'--dataset',a.dataset,'--profile',a.profile,
            '--catalog',a.catalog,'--player',a.player,'--out',a.run],3600):
            raise RuntimeError('Board experiment failed; no promotion')
        j['board_result_review']=review_board_result(a.run);save()
        if run('report',[sys.executable,'-X','utf8',root/'tools/fpga_texture_v170/render_video_report.py',
            '--run',a.run,'--baseline',a.render_baseline,'--previous',a.render_previous,'--label',a.label],300):
            raise RuntimeError('Report rendering failed; review physical records')
        j['status']='EXPERIMENT_COMPLETE_REVIEW_ACTUAL_SPEED_BEFORE_PROMOTION';save()
    except Exception as e:
        j.update(status='FAILED_NO_PROMOTION',error=repr(e));save();raise
    print(json.dumps(j),flush=True)
if __name__=='__main__':main()
