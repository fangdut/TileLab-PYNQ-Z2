from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'host/workstation.py';s=p.read_text()
s=s.replace("'host/jtag_capture.tcl'","'host/event_capture.tcl'")
a=s.index('    def capture(self,threshold):',s.index('class Bridge:'));b=s.index('    @staticmethod',a)
s=s[:a]+'''    def exchange(self,command):
        self.start();key=str(time.time_ns())
        atomic(self.run/'request.txt',f'{command[0]} {key} {command[1]}\\n'.encode())
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            p=self.run/'response.txt'
            if p.exists():
                words=p.read_text().strip().split()
                if len(words)>1 and words[1]==key:
                    if words[0]=='error':raise RuntimeError(' '.join(words[2:]))
                    return key,words
            if self.proc.poll() is not None:raise RuntimeError('JTAG disconnected; unacknowledged events retained')
            time.sleep(.05)
        raise RuntimeError('Transfer timeout; unacknowledged events retained')
    def capture(self,threshold):
        key,words=self.exchange(('capture',str(threshold)))
        if words[0]!='ok' or len(words)!=67:raise ValueError('Malformed event response')
        elapsed=int(words[2]);d=list(map(int,words[3:43]));m=list(map(int,words[43:]))
        rawpath=self.run/f'frame_{key}.bin';raw=rawpath.read_bytes();rawpath.unlink()
        return self.decode_event(raw,d,m,elapsed)
    def ack(self,frame):
        self.exchange(('ack',f"{frame['boot_id']} {frame['event_id']}"))
    @staticmethod
    def decode_event(raw,d,m,elapsed):
        if len(d)!=40 or len(m)!=24 or m[0]!=0x54494c33 or d[34]!=m[2] or d[35]!=3686400:raise ValueError('Invalid queue header')
        f,image,mask=Bridge.decode(raw,d[2],d[3],d[4],d[5],d[6],d[7],m[18],elapsed)
        n=d[9]&15
        if n>8 or d[9]&0x80000000:raise ValueError('Invalid hardware region snapshot')
        boxes=[];areas=[]
        for i in range(n):
            lo,hi=d[10+i*2:12+i*2];box=[lo&65535,lo>>16,hi&65535,hi>>16];area=d[26+i]
            if not(0<=box[0]<=box[2]<1280 and 0<=box[1]<=box[3]<720 and 32<=area<=d[3]):raise ValueError('Invalid PL region coordinates or area')
            boxes.append(box);areas.append(area)
        if sum(areas)>d[3]:raise ValueError('Region areas exceed captured mask')
        f.update(boxes=boxes,region_areas=areas,alarm=bool(n or d[9]&256),region_overflow=bool(d[9]&256),
          event_id=d[0],boot_id=d[34],event_reason=d[8],captured_ms=d[36],queue_depth=m[6],
          event_total=m[7],events_dropped=m[8],board_captures=m[9],invalid_frames=m[10],capture_gaps=m[17],
          algorithm='FPGA_VALLEY17_GRID32_REGIONS8',transport='USB_JTAG_EVENT_QUEUE')
        return f,image,mask
'''+s[b:]
s=s.replace("key=f\"pl_{frame['frame_id']}_{time.time_ns()}\";payload=", "key=(f\"pl_{frame['boot_id']}_{frame['event_id']}\" if 'event_id' in frame else f\"pl_{frame['frame_id']}_{time.time_ns()}\");payload=")
s=s.replace("        with self.lock:\n            if self.db.execute('SELECT COUNT(*)", "        with self.lock:\n            old=self.db.execute('SELECT payload FROM events WHERE id=?',(key,)).fetchone()\n            if old:\n                if json.loads(old[0])['image_sha256']!=payload['image_sha256']:raise ValueError('Event identity reused with different pixels')\n                return key\n            if self.db.execute('SELECT COUNT(*)",1)
s=s.replace("if manual or (frame['alarm'] and not self.incident):", "if manual or frame.get('event_reason') in (1,2) or ('event_id' not in frame and frame['alarm'] and not self.incident):")
s=s.replace("                    self.incident=frame['alarm']", "                    self.incident=frame['alarm']\n                if hasattr(self.bridge,'ack'):self.bridge.ack(frame)")
s=s.replace("limitations='预览为取样帧，检测连续运行；红框为 PL 输出的单个候选区域；合成视频不能证明真实瓷砖准确率。'", "limitations='板端保留最多 12 个待确认事件，满队列会计数告警；FPGA 最多 8 个区域框，邻近缺陷可能合并；合成视频不能证明工业准确率。'")
s=s.replace("{'video','station_0','station_1','station_2','station_3'}", "{'video','station_0','station_1','station_2','station_3','station_4','station_5','burst'}")
p.write_text(s)
p=r/'host/hdmi_display.ps1';s=p.read_text().replace("'^station_[0-3]$'","'^station_[0-5]$'").replace("if($c -eq 'video'){", "if($c -eq 'video' -or $c -eq 'burst'){")
s=s.replace("$media.Source=[Uri](Join-Path $Root 'data/conveyor_SYNTHETIC_720p60.mp4')", "$videoName=if($c -eq 'burst'){'data/burst_SYNTHETIC_720p60.mp4'}else{'data/conveyor_SYNTHETIC_720p60.mp4'};$media.Source=[Uri](Join-Path $Root $videoName)")
p.write_text(s)
