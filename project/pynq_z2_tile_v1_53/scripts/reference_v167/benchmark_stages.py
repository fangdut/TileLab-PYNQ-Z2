"""Measure NumPy and FPGA on the same captured pairs; separate system latency."""
from pathlib import Path
import argparse,sys,json,time,statistics,hashlib
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'));import frame_v167 as model
def main():
    p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();board=json.loads(a.board.read_text());root=a.board.parent/'station';rows=[]
    if board['implementation_sha256']!=model.implementation():raise ValueError('Current algorithm differs from the captured board experiment')
    for r in board['rows']:
        if not r['result'].get('hardware'):continue
        folder=root/r['result']['record'];active=json.loads((root/'calibrations'/r['source']['style']/'active.json').read_text());reference=np.array(Image.open(root/active['bundle']/'reference.png').convert('RGB'));current=np.array(Image.open(folder/'capture/input.png').convert('RGB'));prepared,pair,_,_=model.prepare(reference,current);times=[]
        for _ in range(4):
            started=time.perf_counter();expected=model.oracle(pair,prepared['photometric']);times.append(time.perf_counter()-started)
        actual=np.fromfile(folder/'scores.u32',dtype='<u4').reshape(500,500)
        if not np.array_equal(expected,actual):raise AssertionError('Benchmark does not reproduce board pixels')
        rows.append(dict(source=r['source']['source'],cpu_median_ms=statistics.median(times[1:])*1000,pl_ms=r['result']['hardware']['engine_seconds']*1000,network_request_ms=r['result']['hardware']['request_seconds']*1000,full_operation_ms=r['seconds']*1000))
    result=dict(scope='SAME_CAPTURED_INPUT_NUMPY_FULL_FRAME_ORACLE_VS_ACTUAL_PL_CORE_NOT_END_TO_END_ACCELERATION_CLAIM',board_sha256=hashlib.sha256(a.board.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,cpu_median_ms=statistics.median(r['cpu_median_ms'] for r in rows),pl_median_ms=statistics.median(r['pl_ms'] for r in rows),request_median_ms=statistics.median(r['network_request_ms'] for r in rows),full_median_ms=statistics.median(r['full_operation_ms'] for r in rows))
    with a.out.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
