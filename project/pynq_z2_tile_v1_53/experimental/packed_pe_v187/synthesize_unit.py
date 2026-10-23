"""Count actual synthesized primitives in the isolated PE, not a complete design."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);source=Path(__file__).with_name('packed_pe.sv');started=time.monotonic()
    script='\n'.join([
        'set_param general.maxThreads 2',
        'read_verilog -sv {'+source.as_posix()+'}',
        'synth_design -top packed_pe -part xc7z020clg400-1 -mode out_of_context',
        'create_clock -period 8.000 [get_ports clk]',
        'report_utilization -file utilization.rpt',
        'report_timing_summary -file synthesis_timing.rpt',
        'set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]',
        'set f [open primitive_count.txt w]; puts $f "DSP48E1=$dsp"; close $f',
        'if {$dsp != 1} {error "Expected exactly one shared DSP48E1"}',
        'write_checkpoint -force packed_pe.dcp', 'exit'])+'\n'
    tcl=a.out/'synth.tcl';tcl.write_text(script)
    with (a.out/'console.log').open('w') as log:
        subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(tcl)],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    count=(a.out/'primitive_count.txt').read_text();assert count.strip()=='DSP48E1=1'
    j=dict(scope='ISOLATED_PE_SYNTHESIS_NOT_ROUTED_DETECTOR_OR_BOARD',passed=True,dsp48e1=1,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        elapsed_seconds=time.monotonic()-started,integrated_into_detector=False)
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
