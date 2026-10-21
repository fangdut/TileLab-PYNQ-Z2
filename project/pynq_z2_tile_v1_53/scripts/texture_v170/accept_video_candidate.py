"""One-off guarded physical iteration, never competition final acceptance.

Wait for a fresh timing-closed candidate, build transport, volatile-program,
recheck all 117 numerical outputs, independently calibrate HDMI, inspect good
and crack captures, and run the exposed 117-photo HDMI experiment. Runtime
image detection remains entirely PL; Python reference checks are offline.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time


def main():
    p=argparse.ArgumentParser()
    for name in ['hardware','hls','dataset','profile','catalog','player','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--previous-source',type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    scripts=root/'scripts/texture_v170';tools=root/'tools/fpga_texture_v170'
    python=Path(os.environ.get('TILELAB_PYTHON','D:/Vivado/TileLab_Runtime_V168/Scripts/python.exe'))
    journal=dict(scope='GUARDED_EXPOSED_DEVELOPMENT_PHYSICAL_ITERATION_NOT_FINAL_ACCEPTANCE',
        hardware=str(a.hardware),stages=[],status='WAITING_FOR_HARDWARE',flash_written=False)
    def save():
        (a.out/'progress.json').write_text(json.dumps(journal,indent=2)+'\n')
    def run(name,args,env=None,timeout=900):
        journal['status']=name;save();start=time.time()
        print(json.dumps(dict(stage=name,state='started')),flush=True)
        with (a.out/(name+'.log')).open('w') as log:
            r=subprocess.run([str(v) for v in args],cwd=root,env=env,stdout=log,
                             stderr=subprocess.STDOUT,timeout=timeout)
        journal['stages'].append(dict(name=name,returncode=r.returncode,seconds=time.time()-start));save()
        if r.returncode:raise RuntimeError(name+' failed; inspect stage log')
        print(json.dumps(dict(stage=name,state='passed')),flush=True)
    def close_source(folder):
        if folder and folder.exists():
            (folder/'command.txt').write_text('close\n')
            status=folder/'status.json'
            for _ in range(50):
                try:
                    if not json.loads(status.read_text()).get('running'):return
                except (OSError,ValueError):pass
                time.sleep(.1)
            raise RuntimeError('Previous owned source did not close; no new source opened')
    def select_photo(ident):
        (source/'command.txt').write_text('photo:'+ident+'\n')
        for _ in range(100):
            try:
                s=json.loads((source/'status.json').read_text())
                if s['running'] and s['paused'] and s['image_id']==ident and s['physical_window_bounds_verified']:
                    time.sleep(.7);return
            except (OSError,ValueError):pass
            time.sleep(.1)
        raise RuntimeError('Owned photo source did not acknowledge input')
    def video(name,profile=None,seconds=5,leave=False):
        args=[python,scripts/'video_control.py','--hardware',a.hardware,'--program',program,
            '--validation',board,'--out',a.out/name,'--seconds',seconds]
        if profile:args+=['--color-profile',profile]
        if leave:args+=['--leave-running']
        run(name,args,timeout=150)
    def snapshot(name,video_name):
        run(name,[python,scripts/'video_snapshot.py','--hardware',a.hardware,
            '--video',a.out/video_name,'--out',a.out/name],timeout=240)
    source=a.out/'source';player=None
    try:
        save();deadline=time.time()+5400
        while True:
            status=a.hardware/'implementation_status.json'
            if status.exists():
                s=json.loads(status.read_text())
                if s['setup_slack_ns']<0 or s['hold_slack_ns']<0 or s['drc_errors']:
                    raise RuntimeError('Physical timing/DRC failed; programming blocked')
                sealed=a.hardware/'candidate_preflight.json'
                console=a.hardware.with_name(a.hardware.name+'_console.log')
                if sealed.exists():
                    repaired=a.hardware/'physical_repair.json'
                    original_pass='TEXTURE_V170_IMPLEMENTATION_PASSED' in console.read_text(errors='replace')
                    if repaired.exists():
                        proof=json.loads(repaired.read_text())
                        if proof['scope']!='TIMING_CLOSED_POSTROUTE_PHYSICAL_REPAIR_NOT_PROGRAMMED':
                            raise ValueError('Wrong repair proof scope')
                        for key in ['bit','xsa']:
                            if hashlib.sha256((a.hardware/('system.'+key)).read_bytes()).hexdigest()!=proof[key+'_sha256']:
                                raise ValueError('Physical repair export identity mismatch')
                        original_pass=True
                    if not original_pass:
                        raise RuntimeError('Hardware build did not report successful guarded export')
                    if (a.hardware/'system.xsa').exists() and (a.hardware/'system.bit').exists():break
            if time.time()>deadline:raise TimeoutError('Hardware did not complete')
            time.sleep(10)
        # The build writes export files only after timing/DRC/Gray-skew checks.
        # Verify actual artifacts again inside the software/programming tools.
        software=a.out/'software.sdk';program=a.out/'program';board=a.out/'board117'
        env=os.environ.copy()
        env.update(TILE_TEXTURE_SW=str(software),TILE_TEXTURE_HW=str(a.hardware),
            TILE_TEXTURE_HLS=str(a.hls),TILE_TEXTURE_MODEL=str(a.profile))
        run('build_transport',['D:/2025.2/Vitis/bin/vitis.bat','-s',scripts/'build_software.py'],env,1200)
        close_source(a.previous_source)
        run('volatile_program',[python,scripts/'program_board.py','--hardware',a.hardware,
            '--software',software,'--out',program],timeout=300)
        run('direct117',[python,tools/'validate_board.py','--dataset',a.dataset,
            '--profile',a.profile,'--program',program,'--out',board],timeout=600)
        source.mkdir();(source/'command.txt').write_text('calibrate\n')
        stdout=(source/'stdout.log').open('w');stderr=(source/'stderr.log').open('w')
        player=subprocess.Popen([str(a.player),str(a.catalog),str(source/'status.json'),'4',str(source/'command.txt')],stdout=stdout,stderr=stderr)
        (source/'pid.txt').write_text(str(player.pid)+'\n')
        ready=False
        for _ in range(400):
            if player.poll() is not None:raise RuntimeError('HDMI source exited; inspect stderr')
            try:
                s=json.loads((source/'status.json').read_text())
                if s['running'] and s['calibration_pattern'] and s['physical_window_bounds_verified']:
                    ready=True;break
            except (OSError,ValueError):pass
            time.sleep(.1)
        if not ready:raise RuntimeError('HDMI calibration source not ready')
        video('identity_gray_live');snapshot('identity_gray_snapshot','identity_gray_live')
        color=a.out/'color_profile.json'
        run('derive_color_profile',[python,tools/'calibrate_hdmi_color.py','--snapshot',a.out/'identity_gray_snapshot',
            '--model',a.profile/'model.bin','--out',color])
        for label,ident in [('good','6621d769324f6e05d5838381'),('crack','6621d769324f6e05d583835f')]:
            select_photo(ident)
            video(label+'_live',color);snapshot(label+'_snapshot',label+'_live')
            run(label+'_offline_reference_audit',[python,tools/'audit_captured_reference.py',
                '--profile',a.profile,'--image',a.out/(label+'_snapshot/actual_hdmi_input.png'),
                '--result',a.out/(label+'_snapshot/raw_result.bin'),'--out',a.out/(label+'_reference_audit')])
        video('series_live',color,seconds=8,leave=True)
        run('hdmi117',[python,scripts/'video_photo_series.py','--hardware',a.hardware,
            '--video',a.out/'series_live','--catalog',a.catalog,'--source-status',source/'status.json',
            '--source-command',source/'command.txt','--out',a.out/'hdmi117'],timeout=1600)
        direct=json.loads((board/'summary.json').read_text())
        hdmi=json.loads((a.out/'hdmi117/summary.json').read_text())
        speed=json.loads((a.out/'series_live/report.json').read_text())
        passed=hdmi['cases']==117 and hdmi['correct']==117
        journal.update(status='DEVELOPMENT_ACCURACY_PASS_SPEED_TARGET_PENDING' if passed else 'HDMI_ACCURACY_FAILED',
            direct117=direct,hdmi117=hdmi,hdmi_fps=speed['frame_rate'],
            ten_fps_passed=False,short_observation_at_least_ten_fps=speed['frame_rate']>=10,
            sustained_speed_test_required=True,competition_final_acceptance=False,
            benchmark_is_blind=False)
        save();print(json.dumps(journal),flush=True)
    except Exception as error:
        journal.update(status='FAILED_NO_PROMOTION',error=str(error));save();raise
    finally:
        if player is not None and player.poll() is None:
            (source/'command.txt').write_text('close\n')


if __name__=='__main__':main()
