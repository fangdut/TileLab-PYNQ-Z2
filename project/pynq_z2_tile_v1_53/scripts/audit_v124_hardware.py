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
result=dict(passed=True,new_hardware=True,wns_ns=wns,whs_ns=whs,wpws_ns=wpws,resources=used,baseline_resources=dict(lut=17049,ff=28386,bram=58,dsp=2),bus_skew_constraints_met=len(slacks),minimum_bus_skew_slack_ns=min(slacks),cdc_unsafe_endpoints=unsafe,reports_sha256=reports,artifacts_sha256={n:sha(W/n) for n in ('system.bit','system.xsa','system.ltx')},pixel_mhz=74.25,axi_mhz=100,reference_mhz=200,scope='New routed implementation and exported XSA/BIT equality; existing CDC/I/O warnings are reported separately, not waived by this pass flag')
(O/'hardware_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
