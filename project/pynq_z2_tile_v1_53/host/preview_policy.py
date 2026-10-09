"""Budget ordinary image requests, independently of FPGA detection and evidence.

The caller holds the station lock. A deadline is derived from the actual last
ordinary request start, so delayed work never earns a catch-up burst. Event and
manual requests bypass the budget; neither consumes an ordinary preview slot.
"""


class PreviewPolicy:
    POLL_SECONDS = .2

    def __init__(self, fps=0):
        self.fps = 0
        self.last_start = None
        self.preview_requests = 0
        self.priority_requests = 0
        self.deferred_polls = 0
        self.set_rate(fps)

    def set_rate(self, fps):
        if type(fps) is not int or fps not in (0, 2, 5):
            raise ValueError('Preview rate must be the integer 0, 2 or 5')
        self.fps = fps

    def due(self, now):
        return not self.fps or self.last_start is None or now >= self.last_start + 1 / self.fps

    def next_poll(self, now, frozen=False):
        deadline = now + self.POLL_SECONDS
        if not frozen and self.fps and self.last_start is not None:
            deadline = min(deadline, max(now, self.last_start + 1 / self.fps))
        return deadline

    def started(self, now, priority=False):
        if priority:
            self.priority_requests += 1
        else:
            self.last_start = now
            self.preview_requests += 1

    def snapshot(self):
        return dict(event_priority=True, idle_poll_ms=200,
                    preview_requests=self.preview_requests,
                    priority_requests=self.priority_requests,
                    deferred_polls=self.deferred_polls)
