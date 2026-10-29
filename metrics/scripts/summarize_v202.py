"""Recompute archived V202 metrics only. Does not deploy or contact a board."""
from pathlib import Path
import argparse, csv, json

SOURCE = 'project/pynq_z2_tile_v1_53/reports/v202/summary.json'
SPECS = [
    ('development_cases','exact117.cases','images','exposed_development_replay'),
    ('normal_images','exact117.normal_images','images','exposed_development_replay'),
    ('normal_false_alarms','exact117.normal_false_alarms','images','not_independent_accuracy'),
    ('defects_detected','exact117.defects_detected','images','84_defect_development_images'),
    ('pl_mean_ms','exact117.mean_engine_seconds','ms','117_images_PL_kernel'),
    ('transfer_detection_mean_ms','exact117.mean_transfer_detection_seconds','ms','117_images_excludes_decode_UI_review_save'),
    ('fixed_frame_completions','core200.frames','frames','repeated_DDR_frame_not_new_video'),
    ('fixed_frame_pl_fps','core200.sustained_pl_fps','fps','PL_microbenchmark_not_video'),
    ('workflow_inferences','workflow22.physical_inferences','requests','automated_review_API_replay'),
    ('unsafe_actions_blocked','workflow22.controls_rejected','actions','workflow_interlock_checks'),
    ('logical_cycles','soak100.completed_cycles','cycles','script_review_no_physical_actuation'),
    ('logical_released','soak100.released','cycles','logical_only'),
    ('logical_segregated','soak100.segregated','cycles','logical_only'),
    ('cycle_mean_s','soak100.cycle_seconds.mean','s','includes_0.25s_script_review_API_and_disk'),
    ('script_review_hold_s','soak100.review_hold_seconds','s','not_real_human_review'),
    ('finite_test_elapsed_s','elapsed_seconds','s','not_long_term_stability'),
    ('boot_identity','boot_identity','id','finite_test_same_boot'),
]

def rows(repo):
    data=json.loads((repo/SOURCE).read_text(encoding='utf8'))
    out=[]
    for metric,key,unit,scope in SPECS:
        value=data
        for part in key.split('.'): value=value[part]
        if unit=='ms': value*=1000
        out.append(dict(metric=metric,value=repr(value) if isinstance(value,float) else str(value),unit=unit,scope=scope,source=SOURCE,json_field=key))
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[2]
    result=rows(repo)
    with args.out.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    print(f'{len(result)} archived metrics written to {args.out}')

if __name__=='__main__':main()
