"""Map the generated whole detector to real primitives; no board or FPS claim."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys
from check_generated import inspect
p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
gate=inspect(a.hls)
if not (gate['capacity_gate'] and gate['recurrence_safe'] and gate['shared_dot_128_dsp']):raise RuntimeError('Static capacity/recurrence gate failed; do not synthesize this candidate')
a.out.mkdir(parents=True,exist_ok=False)
(a.out/'input_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
rtl=(a.hls/'solution/syn/verilog').resolve();out=a.out.resolve()
tcl='''set_param general.maxThreads 2
cd {%s}
read_verilog [glob *.v]
synth_design -top texture_integer -part xc7z020clg400-1 -mode out_of_context -flatten_hierarchy rebuilt
create_clock -name ap_clk -period 10 [get_ports ap_clk]
report_utilization -file {%s/utilization.rpt}
report_utilization -hierarchical -file {%s/hierarchy.rpt}
report_timing_summary -file {%s/timing_synthesis_only.rpt}
write_checkpoint {%s/detector_synth.dcp}
puts "PAIRED_DETECTOR_OOC_SYNTH_PASS_NOT_ROUTED_OR_BOARD"
exit
''' % (rtl.as_posix(),out.as_posix(),out.as_posix(),out.as_posix(),out.as_posix())
(out/'build.tcl').write_text(tcl)
with (out/'console.log').open('w') as log:r=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-nojournal','-source',str(out/'build.tcl')],cwd=out,stdout=log,stderr=subprocess.STDOUT)
text=(out/'console.log').read_text(errors='replace');passed=r.returncode==0 and 'PAIRED_DETECTOR_OOC_SYNTH_PASS_NOT_ROUTED_OR_BOARD' in text
record=dict(scope='REAL_PRIMITIVE_OOC_SYNTHESIS_NOT_FULL_VIDEO_SYSTEM_NOT_ROUTED_NOT_BOARD',passed=passed,source_sha256=gate['source_sha256'],returncode=r.returncode)
(out/'summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if not passed:sys.exit(2)
