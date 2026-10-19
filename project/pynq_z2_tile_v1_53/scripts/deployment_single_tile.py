"""Read-only integrity gate shared by packaging and volatile programming."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from single_tile_profile import load

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def matching_bit(hardware):
    with zipfile.ZipFile(hardware/'system.xsa') as archive:
        bits=[n for n in archive.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or hashlib.sha256(archive.read(bits[0])).hexdigest()!=sha(hardware/'system.bit'):raise ValueError('XSA embedded BIT differs from standalone BIT')

def verify(bundle):
    bundle=Path(bundle).resolve();p=load(ROOT);m=json.loads((bundle/'DEPLOYMENT.json').read_text(encoding='utf8'))
    if m['release']!='V1.64' or m['profile_sha256']!=p['profile_sha256'] or m['firmware_version']!=0x13200 or m['model_id']!=p['model_id']:raise ValueError('Deployment belongs to another release')
    required={'system.bit','system.xsa','hdmi_ethernet.elf','ps7_init.tcl','implementation_status.txt'}
    if not required.issubset(m['files']):raise ValueError('Incomplete deployment bundle')
    for name,digest in m['files'].items():
        path=(bundle/name).resolve()
        if not path.is_relative_to(bundle) or sha(path)!=digest:raise ValueError('Deployment file mismatch: '+name)
    for name,digest in m['source_sha256'].items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=digest:raise ValueError('Source differs from compiled deployment: '+name)
    status=dict(line.split('=',1) for line in (bundle/'implementation_status.txt').read_text().splitlines() if '=' in line)
    if float(status['setup_slack_ns'])<0 or float(status['hold_slack_ns'])<0 or int(status['drc_errors']):raise ValueError('Timing/DRC gate failed')
    matching_bit(bundle)
    return m
