"""Recheck release sources and every archived actual-board score on any host."""
from pathlib import Path
import sys,json,zipfile,hashlib,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'));sys.path.insert(0,str(R/'scripts/reference_v167'))
import frame_v167
from program_release import verify
def main():
    report=R/'reports/v167';bundle=R/'releases/v167_r2';verify(bundle)
    status=json.loads((report/'STATUS.json').read_text());board=json.loads((report/'board_summary.json').read_text())
    assert status['physical_accuracy_qualified'] is False and status['physical_independent_specimens']==0
    assert board['passed'] and board['implementation_sha256']==frame_v167.implementation()
    assert board['programming']['deployment_sha256']==hashlib.sha256((bundle/'DEPLOYMENT.json').read_bytes()).hexdigest()
    archive=report/'board_records.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()==status['board_records_sha256']
    pixels=0
    with zipfile.ZipFile(archive) as z:
        assert z.read('summary.json')==(report/'board_summary.json').read_bytes()
        for row in board['rows']:
            result=row['result']
            if not result.get('hardware'):continue
            active=json.loads(z.read('station/calibrations/'+row['source']['style']+'/active.json'))
            ref=np.array(Image.open(io.BytesIO(z.read('station/'+active['bundle']+'/reference.png'))).convert('RGB'))
            current=np.array(Image.open(io.BytesIO(z.read('station/'+result['record']+'/capture/input.png'))).convert('RGB'))
            prepared,pair,_,_=frame_v167.prepare(ref,current)
            raw=z.read('station/'+result['record']+'/scores.u32')
            assert hashlib.sha256(raw).hexdigest()==result['hardware']['score_sha256']
            assert np.array_equal(np.frombuffer(raw,dtype='<u4').reshape(500,500),frame_v167.oracle(pair,prepared['photometric']))
            pixels+=250000
    assert pixels==3000000
    for name in ('algorithm_original05','algorithm_opened05','algorithm_fresh03'):
        data=json.loads((report/name/'summary.json').read_text())
        assert data['implementation']==frame_v167.implementation() and data['accuracy_qualified'] is False
        assert any(not row['passed'] for row in data['rows']), 'Weak misses must remain visible'
    faults=json.loads((report/'protocol_faults.json').read_text());assert faults['passed'] and len(faults['rows'])==5
    assert all(r['recovered'] and r['mismatch_pixels']==0 for r in faults['rows'])
    print(json.dumps(dict(passed=True,archived_actual_board_pixels=pixels,physical_accuracy_qualified=False)))
if __name__=='__main__':main()
