"""Called only after successful JTAG bitstream and ELF programming."""
from pathlib import Path
import hashlib,json,datetime,sys
ws=Path(__file__).resolve().parent
app='hdmi_ethernet' if len(sys.argv)>1 and sys.argv[1]=='ethernet' else 'hdmi_monitor'
files=['system.bit','system.xsa',f'{app}/build/{app}.elf']
proof=dict(active_application=app,configured_address=(sys.argv[2] if len(sys.argv)>2 else None),boot_id=json.loads((ws.parent/'reports/current_boot_reservation.json').read_text())['boot_id'],programmed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sha256={name:hashlib.sha256((ws/name).read_bytes()).hexdigest() for name in files})
p=ws.parent/'reports/programmed_v153.json';tmp=p.with_suffix('.json.tmp')
tmp.write_text(json.dumps(proof,indent=2));tmp.replace(p)
