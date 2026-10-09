"""Collect measured facts; explicitly retain recognition failures/known limits."""
from pathlib import Path
import datetime,hashlib,json,re
R=Path(__file__).resolve().parents[1];O=R/'reports/v153';S=R/(R.name+'.sdk')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    narrow=load(O/'real_board/summary.json');wide=load(O/'real_board_wide/summary.json')
    external=load(O/'external_mcs2/summary.json');motion=load(O/'submission_motion/summary.json')
    transport=load(O/'transport_comparison.json')
    for name,item in [('narrow',narrow),('wide',wide),('external engineering',external),('motion',motion),('transport',transport)]:assert item['passed'],name
    assert narrow['pixel_exact']==wide['pixel_exact']==50 and external['samples']==24
    tests=(O/'host_tests_final.log').read_text(encoding='utf-8-sig')
    assert '\nOK' in tests and 'FAILED' not in tests
    count=int(re.search(r'Ran (\d+) tests',tests).group(1))
    frontend={p.stem:load(p) for p in (O/'frontend').glob('*.json')}
    assert len(frontend)==6 and all(v['passed'] for v in frontend.values())
    diagnostics={kind:load(O/('diagnostics_'+kind)/'summary.json') for kind in ('board','loopback')}
    assert all(v['passed'] for v in diagnostics.values())
    for report in (narrow,wide):
        assert report['source_sha256'][str(R/'host/workstation.py')]==sha(R/'host/workstation.py')
    plan=load(R/'ITERATION_PLAN.json');proof=load(R/'reports/programmed_v153.json')
    for name in ('system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'):
        assert sha(S/name)==plan['inherited_hardware_sha256'][name]==proof['sha256'][name]
    assert (R/(R.name+'.xpr')).exists() and list((S/'hdmi_platform').rglob('*.xpfm'))
    assert 'All user specified timing constraints are met' in (R/'reports/timing_summary.rpt').read_text()
    result=dict(version='V1.53',status='BOARD_VALIDATED_SELECTED_MATERIAL_COMPETITION_PROTOTYPE',
                engineering_acceptance=True,universal_material_recognition_accepted=False,
                scope='720p60 FPGA candidate detection and durable per-product review for calibrated material; real photos with synthetic motion; no industrial camera or factory claim',
                collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),host_tests=count,frontend=frontend,diagnostics=diagnostics,
                narrow=narrow,wide=wide,external=external,motion=motion,transport=transport,
                bit_sha256=sha(S/'system.bit'),xsa_sha256=sha(S/'system.xsa'),elf_sha256=sha(S/'hdmi_ethernet/build/hdmi_ethernet.elf'),
                hardware_firmware='0x12b00',hardware_origin='unchanged routed V1.52 image, physically tested with V1.53 station',
                timing_wns_ns=.030,timing_whs_ns=.050,bram_percent=74.64,
                remaining_limits=['External material 1/24 alarms, no normal whole-tile FPR','No camera/factory independent product trials','Measured source-file RGB differs from HDMI acquisition','Previous-frame HDMI boxes','Finite 12-event/48-slot cache; cannot retain indefinitely or across board power loss','Narrow timing margins; no overclock claim','Physical HDMI unplug/relock and 24h endurance not certified'],
                proof_sha256={str(p.relative_to(R)).replace('\\','/'):sha(p) for p in [O/'real_board/summary.json',O/'real_board_wide/summary.json',O/'external_mcs2/summary.json',O/'submission_motion/summary.json',O/'transport_comparison.json',O/'host_tests_final.log',R/'reports/programmed_v153.json']})
    (O/'final_validation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],host_tests=count,external_alarms=external['crack_alarms'],automatic_evidence=motion['automatic_archives'])))
if __name__=='__main__':main()
