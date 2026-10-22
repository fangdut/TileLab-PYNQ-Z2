from pathlib import Path
import sys,json,copy,hashlib
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sys.path.insert(0,str(P/'scripts/texture_v170'));from run_physical_trial import review_board_result
out=W/'v180_board_review_checks01';out.mkdir(exist_ok=False)
positives=[review_board_result(W/'v173_acceptance08'),review_board_result(W/'v179_acceptance01')]
relative=['progress.json','board117/summary.json','hdmi117/summary.json'];original={n:json.loads((W/'v179_acceptance01'/n).read_text()) for n in relative};negative=[]
for case in ['helper_returned_zero_but_accuracy_failed','normal_false_alarm','arm_running','cpu_frame_start','stale_input','wrong_fps']:
    docs=copy.deepcopy(original);hdmi=docs['hdmi117/summary.json']
    if case=='helper_returned_zero_but_accuracy_failed':docs['progress.json']['status']='HDMI_ACCURACY_FAILED'
    if case=='normal_false_alarm':hdmi['normal_false_alarms']=1;hdmi['correct']=116
    if case=='arm_running':hdmi['both_arm_cores_halted']=False
    if case=='cpu_frame_start':hdmi['cpu_per_frame_start_writes']=1
    if case=='stale_input':hdmi['distinct_observed_photo_crcs']=116
    if case=='wrong_fps':hdmi['autonomous_hdmi_fps_over_photo_series']+=1
    folder=out/case
    for name,value in docs.items():p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
    try:review_board_result(folder)
    except ValueError as e:negative.append(dict(case=case,rejected=True,error=str(e)))
    else:raise AssertionError('Invalid physical evidence accepted: '+case)
j=dict(scope='PHYSICAL_REVIEW_POSITIVE_AND_MUTATED_NEGATIVE_FIXTURES_NOT_NEW_BOARD_RUN',passed=True,positive=positives,negative=negative,reviewer_source_sha256=hashlib.sha256((P/'scripts/texture_v170/run_physical_trial.py').read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
