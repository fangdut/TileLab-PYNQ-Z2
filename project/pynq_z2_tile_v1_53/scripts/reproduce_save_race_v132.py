"""Reproduce V1.32's archive race using two isolated connections and real PNGs.

Reads the sealed V1.32 Python source without creating bytecode. All image and
database fixtures are temporary; only the JSON result is retained in V1.33.
This deliberately drives the old, unreserved-writer schedule. It is not the
post-fix test: use host/test_archive_concurrency.py for V1.33.
"""
import sys
sys.dont_write_bytecode=True
import hashlib
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

BASELINE=Path('D:/Vivado/pynq_z2_tile_v1_32')
OUTPUT=Path(__file__).resolve().parents[1]/'reports/v133/baseline_save_race.json'
sys.path.insert(0,str(BASELINE/'host'))
import numpy as np
from workstation import Records,atomic,png


def run():
    with tempfile.TemporaryDirectory(prefix='tile_v133_baseline_race_') as directory:
        a,b=Records(directory),Records(directory)
        entered=threading.Event();resume=threading.Event();errors=[]
        frame=dict(boot_id=17,event_id=90,frame_id=73)
        late_image=png(np.full((16,24,3),73,np.uint8));late_mask=png(np.zeros((16,24),np.uint8))
        committed_image=png(np.full((16,24,3),74,np.uint8));committed_mask=png(np.full((16,24),255,np.uint8))
        def intercept(path,data):
            if threading.current_thread().name=='stale-writer' and path.name=='pl_17_90.png':
                entered.set()
                if not resume.wait(15):raise TimeoutError('Did not release stale writer')
            return atomic(path,data)
        def stale():
            try:a.save(frame,late_image,late_mask,'isolated_v132_race')
            except Exception as error:errors.append(dict(type=type(error).__name__,message=str(error)))
        writer=threading.Thread(target=stale,name='stale-writer')
        try:
            with patch('workstation.atomic',side_effect=intercept):
                writer.start()
                if not entered.wait(5):raise TimeoutError('First writer did not reach publication')
                try:
                    key=b.save(dict(frame,frame_id=74),committed_image,committed_mask,'isolated_v132_race')
                    b.update(key,'confirmed_crack','Human review retained')
                    before_verified=b.read_image(key)[0]==committed_image
                finally:resume.set();writer.join(6)
            if writer.is_alive():raise TimeoutError('Stale writer did not exit')
            row=b.get(key);actual=(Path(directory)/'review_records'/f'{key}.png').read_bytes()
            try:b.read_image(key);integrity=dict(passed=True)
            except Exception as error:integrity=dict(passed=False,type=type(error).__name__,message=str(error))
            return dict(
                scenario='Two independent Records connections race on one event before file publication',
                source=str(BASELINE/'host/workstation.py'),
                source_sha256=hashlib.sha256((BASELINE/'host/workstation.py').read_bytes()).hexdigest(),
                temporary_fixture_only=True,bytecode_disabled=sys.dont_write_bytecode,
                committed_evidence_verified_before_stale_write=before_verified,
                stale_writer_errors=errors,committed_row_count=b.summary()['total'],
                committed_frame_id=row['frame_id'],review=row['review'],note=row['note'],
                committed_image_sha256=hashlib.sha256(committed_image).hexdigest(),
                actual_image_sha256=hashlib.sha256(actual).hexdigest(),
                actual_pixels_from_failed_writer=actual==late_image,
                integrity_after_stale_write=integrity,
                reproduced=before_verified and actual==late_image and not integrity['passed'] and
                    row['frame_id']==74 and len(errors)==1 and errors[0]['type']=='IntegrityError')
        finally:
            resume.set()
            if writer.ident is not None:writer.join(6)
            a.db.close();b.db.close()


if __name__=='__main__':
    result=run();OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['reproduced']:raise SystemExit('Expected V1.32 failure was not reproduced')
