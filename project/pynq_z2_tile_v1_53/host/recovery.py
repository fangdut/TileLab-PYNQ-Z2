"""Retry scheduling only. Data integrity failures are never retryable here."""
class TransientTransportError(ConnectionError):
    pass

class Recovery:
    def __init__(self,window=30.0):
        self.window=window;self.episodes=0;self.recovered=0;self.reset()
    def reset(self):
        self.started=None;self.next_retry=0.0;self.attempts=0;self.last_error='';self.exhausted=False
    def failed(self,now,error):
        if self.started is None:self.started=now;self.episodes+=1
        self.attempts+=1;self.last_error=str(error)
        self.next_retry=now+min(2.0,.25*2**min(self.attempts-1,3))
    def expired(self,now):
        return self.started is not None and now-self.started>=self.window
    def ready(self,now):return now>=self.next_retry
    def success(self):
        restored=self.started is not None
        if restored:self.recovered+=1
        self.reset();return restored
    def snapshot(self,now):
        return dict(active=self.started is not None and not self.exhausted,exhausted=self.exhausted,attempts=self.attempts,
                    next_retry_seconds=round(max(0,self.next_retry-now),2),
                    remaining_seconds=round(max(0,self.window-(now-self.started)),2) if self.started is not None else self.window,
                    episodes=self.episodes,recovered=self.recovered,last_error=self.last_error)
