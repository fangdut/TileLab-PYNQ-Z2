"""Publish bounded-age player telemetry without blocking HTTP/capture control.

A cached READY is revoked on read failure or expiry. Keeping the last source
name must never imply fresh input confirmation.
"""
import copy
import math
import threading
import time


class LiveStatusCache:
    def __init__(self, snapshot, interval=.25, stop=None, freshness=1.5):
        if (not callable(snapshot) or type(interval) not in (int, float)
                or not math.isfinite(interval) or interval <= 0
                or type(freshness) not in (int, float)
                or not math.isfinite(freshness) or freshness <= 0):
            raise ValueError('Invalid live status cache configuration')
        self._snapshot = snapshot
        self._stop_pred = stop or (lambda: False)
        self._interval = float(interval)
        self._freshness = float(freshness)
        self._lock = threading.Lock()
        self._value = None
        self._updated = None
        self._error = ''
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run,
                                       name='tilelab-live-status', daemon=True)
        self.thread.start()

    def _run(self):
        while not self._stop.is_set() and not self._stop_pred():
            try:
                value = self._snapshot()
                if not isinstance(value, dict):
                    raise TypeError('Player snapshot must be a dictionary')
                value = copy.deepcopy(value)
                with self._lock:
                    self._value = value
                    self._updated = time.monotonic()
                    self._error = ''
            except Exception as error:
                with self._lock:
                    self._error = f'{type(error).__name__}: {error}'
            self._stop.wait(self._interval)

    def read(self):
        with self._lock:
            value = copy.deepcopy(self._value)
            updated, error = self._updated, self._error
        if value is None:
            return dict(requested=None, request_id=None, observed=None,
                        state='TELEMETRY_PENDING', ready=False,
                        identity_confirmed=False, age_seconds=None,
                        motion=dict(state='UNCONFIRMED', progressing=None,
                                    message='等待播放器状态读取'),
                        message='等待首次播放器状态；板端采集独立继续',
                        cache_ready=False, cache_age_seconds=None,
                        cache_error=error or 'waiting for first snapshot')
        elapsed = max(0., time.monotonic() - updated)
        age = value.get('age_seconds')
        if isinstance(age, (int, float)):
            value['age_seconds'] = round(age + elapsed, 3)
        expired = (elapsed > self._freshness or
                   (isinstance(age, (int, float)) and age + elapsed > self._freshness))
        if error or expired:
            value.update(ready=False, identity_confirmed=False,
                         state='TELEMETRY_ERROR' if error else 'TELEMETRY_STALE',
                         message='播放器状态读取失败或已过期；暂不确认输入，板端采集独立继续',
                         motion=dict(state='UNCONFIRMED', progressing=None,
                                     message='播放器遥测不可用，暂不判断运动'))
        value.update(cache_ready=True, cache_age_seconds=round(elapsed, 3),
                     cache_error=error)
        return value

    def close(self):
        self._stop.set()
        self.thread.join(timeout=1)
