from pathlib import Path
import re,json
R=Path(__file__).resolve().parents[1]
s=(R/'reports/timing_summary.rpt').read_text();start=s.index('WNS(ns)');tail=s[start:].splitlines();numbers=None
for line in tail[1:10]:
    if re.match(r'\s*-?\d+\.\d+',line):numbers=line.split();break
assert numbers
util=(R/'reports/utilization.rpt').read_text()
def amount(label):
    m=re.search(r'\|\s*'+label+r'\s*\|\s*([\d.]+)',util);return float(m.group(1)) if m else None
cdc_rows=[]
for line in (R/'reports/cdc.rpt').read_text().splitlines():
    m=re.search(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',line)
    if m and line.startswith(('Critical','Warning','Info')):
        endpoints,safe,unsafe,unknown,no_async=map(int,m.groups())
        cdc_rows.append(dict(summary=line[:m.start()].strip(),endpoints=endpoints,safe=safe,unsafe=unsafe,unknown=unknown,no_async_reg=no_async))
assert cdc_rows, 'CDC summary missing'
unsafe=sum(r['unsafe'] for r in cdc_rows)
assert unsafe==5 and all('clk_fpga_1' in r['summary'] and 'PixelClk_int' in r['summary'] for r in cdc_rows if r['unsafe']), 'Unexpected CDC regression'
result=dict(wns_ns=float(numbers[0]),tns_ns=float(numbers[1]),whs_ns=float(numbers[4]),resources=dict(lut=amount('Slice LUTs'),ff=amount('Slice Registers'),bram36=amount('Block RAM Tile'),dsp=amount('DSPs')),clocks_mhz=dict(pixel=74.25,dma=100,reference=200),legacy_hdmi_cdc_unsafe_endpoints=unsafe,cdc_summary=cdc_rows)
assert result['wns_ns']>=0 and result['whs_ns']>=0 and result['tns_ns']==0
skew=re.findall(r'Slack\s+\((MET|VIOLATED)\)\s*:\s*([-\d.]+)ns',(R/'reports/bus_skew.rpt').read_text())
assert skew and all(status=='MET' and float(value)>=0 for status,value in skew), 'Bus skew check failed'
result['bus_skew_constraints_checked']=len(skew)
result['bus_skew_min_slack_ns']=min(float(value) for _,value in skew)
assert not re.search(r'\|\s*(Critical Warning|Error)\s*\|',(R/'reports/drc.rpt').read_text()), 'DRC critical violation'
(R/'reports/v15/build_metrics.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
