"""Host-side UART control. Runs on the PC/Jupyter; never processes live video.

The board must already run the matching standalone monitor, loaded with JTAG.
No board is opened unless --port is explicitly supplied.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse, json, re, time

@dataclass
class Profile:
    mode: int = 7
    threshold: int = 120
    source: int = 0
    closing: int = 0
    dark: int = 0
    box: int = 1
    roi: list | None = None
    automatic: int = 1
    margin: int = 40
    reject_area: int = 50

    def validate(self):
        bounds = {'mode':7,'threshold':255,'source':2,'closing':1,'dark':1,
                  'box':1,'automatic':1,'margin':128,'reject_area':921600}
        for k,hi in bounds.items():
            v=getattr(self,k)
            if type(v) is not int or not 0<=v<=hi: raise ValueError(f'invalid {k}')
        if self.reject_area<1: raise ValueError('reject_area must be positive')
        if self.automatic and self.source!=0: raise ValueError('auto requires gray source')
        if self.roi is not None:
            if not isinstance(self.roi,list) or len(self.roi)!=4 or any(type(v)is not int for v in self.roi):
                raise ValueError('ROI needs four integers')
            a,b,c,d=self.roi
            if not (0<=a<=c<1280 and 0<=b<=d<720): raise ValueError('invalid ROI')
        return self

    def commands(self):
        self.validate()
        return ['a 0', f's {self.source}',f'p {self.dark}',f'o {self.closing}',
                'r off' if self.roi is None else 'r '+' '.join(map(str,self.roi)),
                f't {self.threshold}',f'm {self.mode}',f'q {self.box}',f'b {self.margin}',f'a {self.automatic}']

    @classmethod
    def load(cls,path): return cls(**json.loads(Path(path).read_text(encoding='utf8'))).validate()
    def save(self,path): self.validate();Path(path).write_text(json.dumps(asdict(self),indent=2),encoding='utf8')

def parse_line(line):
    # Accept raw UART or timestamped historical "... RX ..." capture lines.
    text=line.split(' RX ',1)[-1].strip()
    if text.startswith('ERROR'): return {'type':'ERROR','text':text}
    if text.startswith('frames='): kind='FRAME'
    else: kind=text.split(' ',1)[0]
    if kind not in {'FRAME','STATS','BRIGHT','AUTO','CONFIG','FEATURE'}: return None
    values={'type':kind}
    for key,value in re.findall(r'(\w+)=([0-9a-fA-F]+)(?=\s|$)',text):
        try: values[key]=int(value,16 if key in {'crc','config','word'} else 10)
        except ValueError: return {'type':'ERROR','text':'malformed telemetry: '+text}
    return values

class QualityGate:
    """A rule-based candidate alarm, NOT a trained product quality classifier.

    Stale snapshots, configuration changes and missing fields yield UNKNOWN.
    Session telemetry must come from a successfully configured monitor.
    """
    def __init__(self,reject_area=50):
        if type(reject_area)is not int or not 1<=reject_area<=921600: raise ValueError('reject area')
        self.reject_area=reject_area;self.last_seq=None;self.config=None
    def update(self,row):
        if not row or row.get('type')!='STATS': return None
        required={'seq','count','status','fresh','config','crc'}
        if not required<=row.keys(): return 'UNKNOWN'
        if row['config']!=self.config:
            self.config=row['config'];self.last_seq=row['seq'];return 'UNKNOWN'
        if row['fresh']!=1 or row['seq']==self.last_seq or not row['status']&1:return 'UNKNOWN'
        self.last_seq=row['seq']
        return 'CANDIDATE_ALARM' if row['count']>=self.reject_area else 'BELOW_AREA_LIMIT'

class Controller:
    def __init__(self,transport): self.transport=transport
    @classmethod
    def connect(cls,port):
        import serial
        return cls(serial.Serial(port,115200,timeout=0.1))
    def close(self): self.transport.close()
    def send(self,command,timeout=3):
        if '\n' in command or '\r' in command: raise ValueError('one command per call')
        self.transport.reset_input_buffer()
        self.transport.write((command+'\n').encode('ascii'));self.transport.flush()
        expected='AUTO_ENABLE' if command.startswith('a ') else 'AUTO_MARGIN' if command.startswith('b ') else 'CONFIG request='
        until=time.monotonic()+timeout;responses=[]
        while time.monotonic()<until:
            line=self.transport.readline().decode('ascii',errors='replace').strip()
            if not line:continue
            responses.append(line)
            if line.startswith('ERROR'): raise RuntimeError(line)
            if line.startswith(expected): return responses
        raise TimeoutError(f'no acknowledgement for {command}')
    def configure(self,profile):
        log=[]
        for command in profile.commands():log += self.send(command)
        return log
    def record(self,seconds,path,reject_area=50):
        if seconds<=0:raise ValueError('positive duration required')
        gate=QualityGate(reject_area);end=time.monotonic()+seconds;count=0
        with Path(path).open('x',encoding='utf8') as out:
            while time.monotonic()<end:
                line=self.transport.readline().decode('ascii',errors='replace').strip()
                if not line:continue
                row=parse_line(line);decision=gate.update(row)
                out.write(json.dumps({'time':time.time(),'raw':line,'parsed':row,'decision':decision})+'\n');count+=1
        if not count:raise RuntimeError('no UART data; no successful test recorded')
        return count

def replay(log,output,reject_area=50):
    gate=QualityGate(reject_area);rows=[]
    for line in Path(log).read_text(encoding='utf-8-sig').splitlines():
        row=parse_line(line)
        if row and row['type']=='STATS':rows.append({**row,'decision':gate.update(row)})
    Path(output).write_text(json.dumps({'mode':'OFFLINE_LOG_REPLAY','rows':rows},indent=2),encoding='utf8')
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port');ap.add_argument('--profile',type=Path)
    ap.add_argument('--seconds',type=float,default=10);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--replay',type=Path);args=ap.parse_args()
    if args.replay:
        if args.port:ap.error('replay and port are mutually exclusive')
        print('offline snapshots',len(replay(args.replay,args.output)));return
    if not args.port or not args.profile:ap.error('live use requires --port and --profile')
    profile=Profile.load(args.profile);ctl=Controller.connect(args.port)
    try:ctl.configure(profile);print('captured lines',ctl.record(args.seconds,args.output,profile.reject_area))
    finally:ctl.close()
if __name__=='__main__':main()
