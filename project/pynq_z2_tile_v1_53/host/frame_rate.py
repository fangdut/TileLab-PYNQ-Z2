"""Estimate live input rate from board snapshots, not archived image timestamps."""
class FrameRate:
    def __init__(self, window_seconds=2.0):
        self.window_seconds=window_seconds
        self.reset()
    def reset(self):
        self.anchor=None
        self.last_time=None
        self.value=None
    def observe(self, count, now, boot):
        if (self.anchor is None or self.anchor[2]!=boot or
            self.last_time is not None and (now<self.last_time or now-self.last_time>5)):
            self.anchor=(now,count,boot);self.last_time=now;self.value=None
            return None
        self.last_time=now
        elapsed=now-self.anchor[0]
        delta=(count-self.anchor[1])&0xffffffff
        if delta>=0x80000000:
            self.anchor=(now,count,boot);self.value=None
        elif elapsed>=self.window_seconds:
            self.value=round(delta/elapsed,1);self.anchor=(now,count,boot)
        return self.value
