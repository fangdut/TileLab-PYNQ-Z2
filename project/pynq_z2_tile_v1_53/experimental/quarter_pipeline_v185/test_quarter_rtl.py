"""Small actual generated-helper simulation, not full detector/board evidence."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,xml.etree.ElementTree as ET

def main():
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    base=Path(__file__).resolve().parent;a.out.mkdir(parents=True,exist_ok=False)
    names=['quarter_horizontal','quarter_vertical']
    reports={}
    for n in names:
        f=a.hls/'solution/syn/report'/(n+'_csynth.xml');r=ET.parse(f).getroot();t=r.find('./PerformanceEstimates/SummaryOfOverallLatency')
        assert t.findtext('Best-caseLatency')==t.findtext('Worst-caseLatency')=='2' and t.findtext('Interval-min')=='1'
        reports[n]=hashlib.sha256(f.read_bytes()).hexdigest()
    sources=[a.hls/'solution/syn/verilog'/('texture_integer_'+n+'.v') for n in names]+[base/'tb_quarter.sv'];started=time.monotonic()
    for name,args in [('xvlog',['-sv',*map(str,sources)]),('xelab',['tb_quarter','-s','test','-debug','typical']),('xsim',['test','-runall'])]:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    text=(a.out/'xsim.log').read_text(errors='replace');marker='QUARTER_PIPELINE_GENERATED_RTL_EXACT_PASS horizontal=262144 vertical=131088'
    if marker not in text or 'Fatal:' in text or 'Error:' in text:raise RuntimeError('Generated quarter helper RTL failed')
    j=dict(scope='GENERATED_QUARTER_UNIT_RTL_NOT_FULL_DETECTOR_TIMING_OR_BOARD',passed=True,
        source_sha256=hashlib.sha256((a.hls/'src/texture_integer.cpp').read_bytes()).hexdigest(),
        exhaustive_signed8_horizontal_inputs=262144,vertical_edge_and_random_cases=131088,
        horizontal_latency_cycles=2,vertical_latency_cycles=2,reported_ii=1,elapsed_seconds=time.monotonic()-started,
        report_sha256=reports,sources={str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
