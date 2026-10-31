"""Verify saved BD clock configuration; this does not measure a running board."""
from pathlib import Path
import argparse,json,hashlib
def verify(hardware,bd_only=False):
    hardware=Path(hardware);bd=hardware/'texture_v170.srcs/sources_1/bd/system/system.bd'
    design=json.loads(bd.read_text())['design'];components=design['components']
    ps=components['ps7']['parameters']
    value=lambda name:float(ps[name]['value'])
    mhz=value('PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ')
    if mhz not in (100,125) or abs(value('PCW_FPGA0_PERIPHERAL_FREQMHZ')-mhz)>.001:
        raise ValueError('Unrecognized or unrealized PL clock')
    hz=int(mhz*1000000)
    if value('PCW_CLK0_FREQ')!=hz:raise ValueError('PS fabric clock configuration disagrees')
    checked={};legacy_derived=[]
    for cell,port in [('pipeline','control_clk'),('video_regs','clk')]:
        if cell not in components:continue
        c=components[cell]
        if int(c['ports'][port]['parameters']['FREQ_HZ']['value'])!=hz:
            raise ValueError('Module clock metadata disagrees: '+cell)
        clocks=[n['ports'] for n in design['nets'].values() if cell+'/'+port in n.get('ports',[])]
        if len(clocks)!=1 or 'ps7/FCLK_CLK0' not in clocks[0]:raise ValueError('Module is not on the checked FCLK0 net')
        for name,bus in c['interface_ports'].items():
            frequency=bus['parameters'].get('FREQ_HZ')
            if frequency is None:
                # Older accepted100MHz BDs record only the associated clock.
                associated=c['ports'][port]['parameters']['ASSOCIATED_BUSIF']['value'].split(':')
                if mhz!=100 or name not in associated:raise ValueError('Missing explicit faster AXI clock metadata')
                legacy_derived.append(cell+'/'+name)
            elif int(frequency['value'])!=hz:
                raise ValueError('AXI clock metadata disagrees: '+cell+'/'+name)
            checked[cell+'/'+name]=hz
    if 'pipeline' in components and value('PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ')!=200:
        raise ValueError('HDMI reference clock changed')
    if 'hpd_startup' in components:
        if int(components['hpd_startup']['parameters']['STARTUP_CYCLES']['value'])!=hz//5:
            raise ValueError('HPD startup no longer200ms at selected clock')
    if not bd_only:
        status=json.loads((hardware/'implementation_status.json').read_text())
        if abs(status['pl_clock_mhz']-mhz)>.001:raise ValueError('Physical status clock differs from PS configuration')
        if 'pl_clock_period_ns' in status and abs(status['pl_clock_period_ns']-1000/mhz)>.001:
            raise ValueError('Actual timing period differs from programmed clock configuration')
        proof=json.loads((hardware/'candidate_preflight.json').read_text())
        if proof.get('requested_pl_clock_mhz',100)!=mhz:raise ValueError('Preflight clock differs from physical implementation')
        if mhz==125 and proof.get('hls_target_clock_ns',10)>8:
            raise ValueError('Faster clock has no matching HLS scheduling proof')
    return dict(scope='SAVED_BLOCK_DESIGN_CLOCK_CONFIGURATION_NOT_RUNNING_FREQUENCY_MEASUREMENT',
                pl_clock_mhz=mhz,axi_clocks_hz=checked,hpd_delay_seconds=.2 if 'hpd_startup' in components else None,
                physical_metadata_checked=not bd_only,legacy_axi_derived_from_checked_clock=legacy_derived,
                bd_sha256=hashlib.sha256(bd.read_bytes()).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('hardware',type=Path);p.add_argument('--bd-only',action='store_true');a=p.parse_args()
    print(json.dumps(verify(a.hardware,a.bd_only)))
