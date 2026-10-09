"""Preserve pending evidence before replacing the live V1.4 receiver."""
import json,time
import board_v13_acceptance as t
s=t.state()
assert s['revision']=='V1.4', 'Only the known V1.4 service may be handed off'
t.action('pause')
while t.state()['busy']:time.sleep(.05)
t.action('display',value='station_6');time.sleep(.6)
drained=0
while t.action('status')['depth']:
    t.shot();drained+=1
after=t.action('status');t.action('disconnect')
(t.R/'reports/v15/v14_handoff.json').write_text(json.dumps(dict(before=s,after=after,drained=drained),indent=2))
print(json.dumps(dict(revision=s['revision'],drained=drained,after=after)))
