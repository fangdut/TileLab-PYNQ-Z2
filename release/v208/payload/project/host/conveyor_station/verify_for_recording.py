# SPDX-License-Identifier: MIT
"""One explicitly automated no-alarm preflight; never records a human review."""
from pathlib import Path
from urllib.request import Request,urlopen
import argparse,json,time

BASE='http://127.0.0.1:8793'
def get():
    with urlopen(BASE+'/api/state',timeout=10) as r:return json.load(r)
def action(op,**extra):
    s=get();body=dict(session=s['session'],revision=s['revision'],op=op,**extra)
    with urlopen(Request(BASE+'/api/action',json.dumps(body).encode(),{'Content-Type':'application/json'}),timeout=10) as r:return json.load(r)
def wait(phase):
    until=time.monotonic()+30
    while time.monotonic()<until:
        s=get()
        if s['phase']=='FAULT':raise RuntimeError(s.get('error'))
        if s['phase']==phase:return s
        time.sleep(.1)
    raise RuntimeError('Preflight timeout')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    before=get()
    if before['phase']!='READY' or not before['closed_loop']['calibrated']:raise RuntimeError('Station must be ready and qualified')
    row=before['samples'][0]
    action('load',sample_id=row['id'],purpose='inspection',conditions_confirmed=True)
    action('inspect',input_held_confirmed=True)
    s=wait('REVIEW_HOLD');r=s['cycle']['result']
    if r['pl_image_alarm']!=0:raise RuntimeError('No-alarm preflight unexpectedly alarmed; left held for review')
    action('automatic_release',policy_id='FPGA_NO_ALARM_AUTO_PASS_V207',result_id=r['id'])
    after=wait('RELEASED')
    assert after['counts']['manual_reviews']==before['counts']['manual_reviews']
    assert after['cycle']['review'] is None
    assert after['connection']['boot_identity']==before['connection']['boot_identity']
    record=dict(scope='RECORDING_PREFLIGHT_AUTOMATED_NO_HUMAN_REVIEW',sample=row,cycle=after['cycle'],
        board_boot_unchanged=True,manual_review_count_unchanged=True,ready=True)
    a.out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(ok=True,frame=r['pl_frame_sequence'],alarm=r['pl_image_alarm'],pl_ms=round(r['pl_engine_seconds']*1000,2),
        transfer_detection_ms=round(r['wall_seconds']*1000,2),manual_review_fabricated=False)))
if __name__=='__main__':main()
