from pathlib import Path
import re,json,hashlib,zipfile
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
t=(R/'reports/timing_summary.rpt').read_text()
assert 'pynq_z2_tile_v1_53/reports/timing_summary.rpt' in t and 'All user specified timing constraints are met' in t
rows=t[t.index('| Design Timing Summary'):].splitlines();line=next(rows[i+2] for i,r in enumerate(rows) if 'WNS(ns)' in r);v=line.split()
wns,whs,wpws=map(float,(v[0],v[4],v[8]));assert min(wns,whs,wpws)>=0
assert all(float(v[k])==0 for k in (1,2,5,6,9,10))
u=(R/'reports/utilization.rpt').read_text();used={}
for name in ('Slice LUTs','Slice Registers','Block RAM Tile','DSPs'):
 match=re.search(r'\|\s*'+re.escape(name)+r'\s*\|\s*([\d.]+)\s*\|',u);assert match,name;used[name]=float(match[1])
drc=(R/'reports/drc.rpt').read_text();assert not re.search(r'\|\s*(?:Error|Critical Warning)\s*\|',drc)
assert sha(W/'system.bit')==sha(R/(R.name+'.runs')/'impl_1/system_wrapper.bit')
with zipfile.ZipFile(W/'system.xsa') as z:
 bits=[n for n in z.namelist() if n.endswith('.bit')];assert len(bits)==1
 assert hashlib.sha256(z.read(bits[0])).hexdigest()==sha(W/'system.bit')
reports={name:sha(R/'reports'/name) for name in ('timing_summary.rpt','utilization.rpt','drc.rpt','cdc.rpt','cdc_details.rpt','methodology.rpt','bus_skew.rpt')}
skew=(R/'reports/bus_skew.rpt').read_text();slacks=[float(x) for x in re.findall(r'Slack \(MET\)\s*:\s*([\d.]+)ns',skew)]
assert len(slacks)==8 and 'VIOLATED' not in skew
cdc=(R/'reports/cdc.rpt').read_text();unsafe=sum(int(line.split()[-3]) for line in cdc.splitlines() if line.startswith(('Critical ','Info ','Warning ')))
assert unsafe==0,'Unsafe CDC endpoints remain'
details=(R/'reports/cdc_details.rpt').read_text()
assert 'CDC-11' not in details and 'Critical' not in details and 'Unknown' not in details
netlist=(O/'reset_netlist.txt').read_text()
assert 'PIXEL_REGISTERS 2' in netlist and 'REFERENCE_REGISTERS 2' in netlist and 'OLD_DUPLICATE_BRIDGES 0' in netlist
recovery=(O/'reference_reset_recovery.rpt').read_text()
assert 'VIOLATED' not in recovery and recovery.count('Slack (MET)')>=3
reset_timing={}
for domain in ('reference','pixel'):
 for check in ('recovery','removal'):
  name=f'{domain}_reset_{check}.rpt';contents=(O/name).read_text()
  assert 'VIOLATED' not in contents and contents.count('Slack (MET)')>=3,name
  values=[float(v) for v in re.findall(r'Slack \(MET\)\s*:\s*([\d.]+)ns',contents)]
  types=re.findall(r'Path Type:\s+(\w+)',contents)
  assert len(values)==3 and types==[check.title()]*3,(name,types)
  reset_timing[name]=dict(sha256=sha(O/name),paths=len(values),minimum_slack_ns=min(values),path_types=types)
result=dict(passed=True,new_hardware=True,wns_ns=wns,whs_ns=whs,wpws_ns=wpws,resources=used,baseline_resources=dict(lut=17217,ff=28940,bram=67,dsp=2),bus_skew_constraints_met=len(slacks),minimum_bus_skew_slack_ns=min(slacks),cdc_unsafe_endpoints=unsafe,reports_sha256=reports,artifacts_sha256={n:sha(W/n) for n in ('system.bit','system.xsa','system.ltx')},pixel_mhz=74.25,axi_mhz=100,reference_mhz=200,scope='New routed reset topology, timing, CDC and exported BIT/XSA equality. Digital/structural checks do not prove analog metastability absence or physical HDMI hotplug recovery.')
result['reset_recovery_removal_reports']=reset_timing
interaction=(O/'implemented_clock_interaction.rpt').read_text()
for a,b in (('PixelClk_int','clk_fpga_0'),('PixelClk_int','clk_fpga_1'),('clk_fpga_0','PixelClk_int'),('clk_fpga_1','PixelClk_int')):
 assert any(line.split()[:2]==[a,b] and 'Asynchronous Groups' in line for line in interaction.splitlines()),(a,b)
result['implemented_clock_evidence_sha256']={n:sha(O/n) for n in ('implemented_clocks.rpt','implemented_clock_interaction.rpt','implemented_applied.xdc','implemented_ignored_exceptions.rpt')}
(O/'hardware_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
