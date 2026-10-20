"""Collect completed experiments without relabeling development data as accuracy."""
from pathlib import Path
import argparse,json,shutil,zipfile,hashlib
R=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    pairs={'program04/proof.json':'programming.json','program04/program.log':'programming.log','board_replay04/summary.json':'board_summary.json','board_faults02/summary.json':'protocol_faults.json','PERFORMANCE_R2.json':'performance.json','service02/result.json':'service_test.json','service02/test.log':'service_test.log'}
    for source,dest in pairs.items():shutil.copy2(a.work/source,a.out/dest)
    for name in ('algorithm_original05','algorithm_opened05','algorithm_fresh03'):
        target=a.out/name;target.mkdir();shutil.copy2(a.work/name/'summary.json',target/'summary.json')
    history=a.out/'research_history';history.mkdir()
    for name in ('holdout01','algorithm_opened01','algorithm_opened04'):
        source=a.work/name/'summary.json'
        if source.exists():shutil.copy2(source,history/(name+'.json'))
    with zipfile.ZipFile(a.out/'board_records.zip','x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in (a.work/'board_replay04').rglob('*'):
            if file.is_file():z.write(file,file.relative_to(a.work/'board_replay04').as_posix())
        for file in (a.work/'player01/data/reference_v167').rglob('*'):
            if file.is_file():z.write(file,'stimuli/'+file.relative_to(a.work/'player01/data/reference_v167').as_posix())
        z.write(a.work/'player01/manifest.json','stimuli_manifest.json')
    status=dict(version='V1.67.2',engineering_pipeline_passed=True,physical_accuracy_qualified=False,physical_independent_specimens=0,weak_single_pixel_misses_preserved=True,scope='SINGLE_TILE_SAME_PATTERN_REFERENCE_FIXED_FIXTURE',partition=dict(alignment='HOST',full_frame_score='PL',components='HOST'),board_records_sha256=hashlib.sha256((a.out/'board_records.zip').read_bytes()).hexdigest())
    (a.out/'STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status))
if __name__=='__main__':main()
