"""Map native shared MAC after its arithmetic/RTL pass. Not a detector result."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--unit-proof',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parent;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
unit=json.loads(a.unit_proof.read_text());assert unit['passed'] and unit['source_sha256']==sha(root/'shared_mac.v') and unit['issued']==2048
a.out.mkdir(exist_ok=False,parents=True);out=a.out.resolve()
tcl='\n'.join(['set_param general.maxThreads 2','read_verilog {'+(root/'shared_mac.v').as_posix()+'}',
 'synth_design -top shared_mac -part xc7z020clg400-1 -mode out_of_context',
 'create_clock -period 10 [get_ports ap_clk]','report_utilization -file utilization.rpt',
 'report_timing_summary -file synthesis_timing.rpt','report_utilization -hierarchical -file hierarchy.rpt',
 'set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]','if {$dsp != 128} {error "Native unit must use128 DSP"}',
 'write_checkpoint unit.dcp','puts "NATIVE_SHARED_MAC_MAPPED_PASS_NOT_DETECTOR_OR_BOARD"','exit'])+'\n'
(out/'build.tcl').write_text(tcl)
with (out/'console.log').open('w') as log:r=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-nojournal','-source',str(out/'build.tcl')],cwd=out,stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0 and 'NATIVE_SHARED_MAC_MAPPED_PASS_NOT_DETECTOR_OR_BOARD' in (out/'console.log').read_text(errors='replace')
s=(out/'utilization.rpt').read_text();values={k:int(re.search(pat,s)[1]) for k,pat in dict(LUT=r'\|\s*Slice LUTs\*\s*\|\s*(\d+)',FF=r'\|\s*Slice Registers\s*\|\s*(\d+)',DSP=r'\|\s*DSPs\s*\|\s*(\d+)').items()}
assert values['DSP']==128
j=dict(scope='NATIVE_SHARED_MAC_ACTUAL_UNIT_MAPPING_NOT_DETECTOR_OR_BOARD',passed=True,source_sha256=sha(root/'shared_mac.v'),c_model_sha256=sha(root/'shared_mac_model.cpp'),unit_proof_sha256=sha(a.unit_proof),**values)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
