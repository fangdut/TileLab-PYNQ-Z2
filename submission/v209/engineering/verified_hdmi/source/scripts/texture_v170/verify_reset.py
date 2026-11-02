"""Check actual BD pin levels, independently of timing and IP co-simulation."""
import json
from pathlib import Path
def verify(hardware):
    path=Path(hardware)/'texture_v170.srcs/sources_1/bd/system/system.bd'
    design=json.loads(path.read_text())['design'];components=design['components'];nets=design['nets']
    def ports(pin):
        found=[n['ports'] for n in nets.values() if pin in n.get('ports',[])]
        if len(found)!=1:raise RuntimeError('Missing/ambiguous connection: '+pin)
        return found[0]
    def constant(pin):
        drivers=[]
        for p in ports(pin):
            name=p.split('/')[0];c=components.get(name,{})
            if ':xlconstant:' in str(c.get('vlnv','')):
                drivers.append(int(c.get('parameters',{}).get('CONST_VAL',{}).get('value','1'),0))
        if len(drivers)!=1:raise RuntimeError('Reset tie-off must have one constant driver: '+pin)
        return drivers[0]
    auxiliary_high=int(components['resets'].get('parameters',{}).get('C_AUX_RESET_HIGH',{}).get('value','0'))
    aux=constant('resets/aux_reset_in');debug=constant('resets/mb_debug_sys_rst');locked=constant('resets/dcm_locked')
    if aux==auxiliary_high or debug!=0 or locked!=1:raise RuntimeError('Fabric is held in reset: check auxiliary polarity, debug reset and clock lock')
    if 'ps7/FCLK_RESET0_N' not in ports('resets/ext_reset_in'):raise RuntimeError('Unexpected external reset source')
    if 'ps7/FCLK_CLK0' not in ports('resets/slowest_sync_clk'):raise RuntimeError('Reset clock is not the PL clock')
    return dict(auxiliary_reset_active_high=auxiliary_high,auxiliary_level=aux,debug_reset=debug,clock_locked=locked,pl_reset_release_checked=True)
