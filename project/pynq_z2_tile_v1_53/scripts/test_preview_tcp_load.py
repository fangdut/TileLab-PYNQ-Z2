"""Bounded loopback integration: real EventTCP + EthernetBridge + Station.

All 1280x720 RAW32 pixels, header CRCs, pixel CRCs, queue identities, SQLite
commits and application ACKs traverse production receiving code. The sender
is a deterministic fixture on 127.0.0.1, NOT a PYNQ or a physical link test.
No measured rate here is a claim about FPGA throughput or Ethernet goodput.
"""
from __future__ import annotations
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import sys
import threading
import time
import traceback
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
import numpy as np
from workstation import EthernetBridge, Station
from tcp_transport import FRAME_BYTES, MAGIC

BOOT = 134
VERSION = 0x12000
CONFIG = (1 << 25) | (1 << 24) | (1 << 23) | (3 << 16) | (90 << 8) | 7
PRODUCTS = (501, 502, 503)
IDLE_SECONDS = 2.2


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def until(predicate, station=None, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if station is not None and station.error:
            raise AssertionError('Station error: ' + station.error)
        if predicate():
            return
        time.sleep(.005)
    raise TimeoutError('Bounded integration-test condition not met')


class FixtureServer:
    """Finite queue with application ACK ownership, using actual TCP sockets."""
    def __init__(self, directory):
        self.directory = directory
        self.lock = threading.RLock()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.listener.settimeout(.2)
        self.port = self.listener.getsockname()[1]
        self.stop = False
        self.connection = None
        self.station = None
        self.queue = deque()
        self.next_event = 1
        self.head = 0
        self.requests = []
        self.acks = []
        self.failures = []
        self.sent_bytes = 0
        self.received_bytes = 0
        self.manual_next = False
        self.started = time.monotonic()
        normal = np.zeros((720, 1280, 4), np.uint8)
        normal[:, :, :3] = [53, 89, 127]
        defect = normal.copy()
        defect[220:280, 800:802, 3] = 1
        self.pixels = {False: normal.tobytes(), True: defect.tobytes()}
        self.crcs = {key: zlib.crc32(value) for key, value in self.pixels.items()}
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def add(self, product=0, manual=False):
        event = dict(event_id=self.next_event, product_id=product,
                     frame_id=10000 + product if product else 20000 + self.next_event,
                     automatic=bool(product), manual=manual, queued_at=time.monotonic())
        self.next_event += 1
        self.queue.append(event)
        return event

    def inject_products(self):
        with self.lock:
            return [dict(self.add(product)) for product in PRODUCTS]

    def meta(self):
        m = [0] * 24
        m[:3] = [0x54494c33, VERSION, BOOT]
        m[4:8] = [self.head, self.next_event - 1, len(self.queue), self.next_event - 1]
        m[9] = max(1, int((time.monotonic() - self.started) * 60))
        m[11] = self.head
        m[15:17] = [90, 1]
        m[18] = m[9]
        m[21] = CONFIG
        return m

    def status(self):
        d = [0] * 40
        d[:6] = [0x484c5431, 1, 1, 1, 0x1000, 1]
        d[14] = len(self.acks)
        d[23:37] = [0x52454331, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1000, 3000, 0]
        return d

    def frame(self, event):
        alarm = event['automatic']
        raw = self.pixels[alarm]
        d = [0] * 40
        d[0:4] = [event['event_id'], 0x10100000, event['frame_id'], 120 if alarm else 0]
        if alarm:
            d[4:6] = [(220 << 16) | 800, (279 << 16) | 801]
            d[9] = 1
            d[10:12] = d[4:6]
            d[26] = 120
        d[6:9] = [13 if alarm else 5, CONFIG, 1 if alarm else 3]
        d[34:40] = [BOOT, FRAME_BYTES, event['frame_id'] * 16,
                    event['product_id'], 32 if alarm else 0, 0x80000000 if alarm else 0]
        m = self.meta()
        m[3] = self.crcs[alarm]
        return d, m, raw

    def acknowledge(self, boot, event_id):
        assert boot == BOOT
        assert self.queue and self.queue[0]['event_id'] == event_id, (event_id, list(self.queue))
        event = self.queue[0]
        station = self.station
        assert station is not None
        # The production receiver sets its frame only after header, payload,
        # pixel CRC, mask/box consistency and PNG conversion have all succeeded.
        frame = station.frame
        assert frame['event_id'] == event_id and frame['boot_id'] == BOOT
        assert frame['pixel_crc_verified'] and frame['header_crc_verified']
        assert frame['descriptor_crc_verified']  # sender's protocol declaration
        assert frame['pixel_crc32'] == self.crcs[event['automatic']]
        assert frame['wire_payload_bytes'] == FRAME_BYTES
        assert frame['event_reason'] == (1 if event['automatic'] else 3)
        saved = False
        key = None
        if event['automatic'] or event['manual']:
            key = f'tile_{BOOT}_{event["product_id"]}' if event['automatic'] else f'pl_{BOOT}_{event_id}'
            db = sqlite3.connect(self.directory / 'review_records/inspection.sqlite3')
            try:
                row = db.execute('SELECT payload FROM events WHERE id=?', (key,)).fetchone()
                assert row is not None, 'ACK arrived before durable event INSERT/COMMIT'
                payload = json.loads(row[0])
                pending = json.loads(db.execute('SELECT payload FROM pending_confirmation WHERE id=1').fetchone()[0])
                for field in ('boot_id', 'event_id', 'frame_id', 'product_id', 'pixel_crc32', 'recovery_generation'):
                    assert pending['frame'][field] == frame.get(field)
                assert pending['record_id'] == key
                assert pending['endpoint'] == f'tcp://127.0.0.1:{self.port}'
                for suffix, name in (('.png', 'image_sha256'), ('_mask.png', 'mask_sha256')):
                    data = (self.directory / 'review_records' / (key + suffix)).read_bytes()
                    assert hashlib.sha256(data).hexdigest() == payload[name]
                saved = True
            finally:
                db.close()
        self.queue.popleft()
        self.head = event_id
        self.acks.append(dict(event, ack_at=time.monotonic(), saved_before_ack=saved,
                              record_id=key, header_crc_verified=True, pixel_crc_verified=True,
                              pixel_crc32=frame['pixel_crc32']))

    def reply(self, op, a, b):
        raw = b''
        event = None
        with self.lock:
            now = time.monotonic()
            if op == 1:
                assert a == 90
                assert b == 4  # raw transport, enhanced detector, four passes
                if not self.queue:
                    self.add(manual=self.manual_next)
                    self.manual_next = False
                event = self.queue[0]
                d, m, raw = self.frame(event)
                code, flags = 0, 15
            else:
                assert op in (2, 3, 5), op
                if op == 2:
                    self.acknowledge(a, b)
                if op == 5:
                    assert a == 90 and b == 4
                d, m = self.status(), self.meta()
                code, flags = 1, 5
            header = struct.pack('<68I', MAGIC, code, len(raw), flags, *d, *m)
            response = header + struct.pack('<I', zlib.crc32(header)) + raw
            self.requests.append(dict(op=op, a=a, b=b, at=now, response_bytes=len(response),
                                      event_id=event['event_id'] if event else None,
                                      product_id=event['product_id'] if event else None))
            return response

    def serve(self):
        try:
            while not self.stop:
                try:
                    connection, _ = self.listener.accept()
                except socket.timeout:
                    continue
                self.connection = connection
                connection.settimeout(.2)
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with connection:
                    request = bytearray()
                    while not self.stop:
                        try:
                            part = connection.recv(16 - len(request))
                        except socket.timeout:
                            continue
                        if not part:
                            break
                        request.extend(part)
                        with self.lock:
                            self.received_bytes += len(part)
                        if len(request) != 16:
                            continue
                        magic, op, a, b = struct.unpack('<4I', request)
                        assert magic == MAGIC
                        request.clear()
                        response = self.reply(op, a, b)
                        # Send actual socket bytes. No capture method is stubbed.
                        connection.sendall(response)
                        with self.lock:
                            self.sent_bytes += len(response)
        except Exception:
            if not self.stop:
                self.failures.append(traceback.format_exc())
        finally:
            self.listener.close()

    def snapshot(self):
        with self.lock:
            return dict(requests=list(self.requests), acks=list(self.acks),
                        received_bytes=self.received_bytes, sent_bytes=self.sent_bytes,
                        queue_depth=len(self.queue), failures=list(self.failures))

    def close(self):
        self.stop = True
        if self.connection:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.thread.join(3)
        assert not self.thread.is_alive()


def paused(station):
    station.action(dict(op='pause'))
    until(lambda: not station.busy, station)
    assert station.pending_ack is None and not station.pending_stats


def run_case(directory, fps):
    directory.mkdir(parents=True)
    (directory / 'host').mkdir()
    server = FixtureServer(directory)
    bridge = EthernetBridge('127.0.0.1')
    bridge.transport.port = server.port
    bridge.transport.compression = False
    bridge.passes = 4
    station = Station(directory, bridge)
    station.threshold = 90
    server.station = station
    try:
        station.action(dict(op='preview_rate', value=fps))
        station.action(dict(op='storage', mode='archive', max_archive_mib=16))
        assert station.state()['preview_rate_supported']
        idle_start = time.monotonic()
        station.action(dict(op='start'))
        until(lambda: time.monotonic() - idle_start >= IDLE_SECONDS, station)
        paused(station)
        idle_end = time.monotonic()
        idle = server.snapshot()
        idle_captures = [r for r in idle['requests'] if r['op'] == 1]
        idle_stats = [r for r in idle['requests'] if r['op'] == 3]
        assert len(idle_captures) >= 3 and len(idle_stats) >= len(idle_captures)
        assert station.records.summary()['total'] == 0
        assert all(not item['saved_before_ack'] for item in idle['acks'])
        gaps = [b['at'] - a['at'] for a, b in zip(idle_captures, idle_captures[1:])]
        if fps:
            assert all(gap >= 1 / fps - .015 for gap in gaps), gaps
        deferred = station.state()['preview_policy']['deferred_polls']
        assert not fps or deferred > 0

        # Same three product identities at every preview setting. A paused
        # station starts with a non-empty retained queue, then must drain it.
        queued = server.inject_products()
        queue_start = time.monotonic()
        station.action(dict(op='start'))
        until(lambda: len([a for a in server.snapshot()['acks'] if a['automatic']]) == len(PRODUCTS), station)
        paused(station)
        after_queue = server.snapshot()
        automatic = [a for a in after_queue['acks'] if a['automatic']]
        assert [a['product_id'] for a in automatic] == list(PRODUCTS)
        assert [a['event_id'] for a in automatic] == [a['event_id'] for a in queued]
        assert all(a['saved_before_ack'] for a in automatic)
        assert station.records.summary()['total'] == len(PRODUCTS)
        assert station.auto_saved == len(PRODUCTS)

        # Establish a fresh ordinary-preview deadline, then request a manual
        # frame while it is still in the future. Both actions are production API.
        count = station.captures
        station.action(dict(op='start'))
        until(lambda: station.captures > count and not station.busy, station)
        paused(station)
        with station.lock:
            last = station.preview_policy.last_start
            deadline = last + 1 / fps if fps else None
        manual_requested = time.monotonic()
        with server.lock:
            assert not server.queue
            server.manual_next = True
        station.action(dict(op='capture'))
        until(lambda: any(a['manual'] for a in server.snapshot()['acks']) and not station.busy, station)
        manual_ack = next(a for a in server.snapshot()['acks'] if a['manual'])
        manual_request = next(r for r in server.snapshot()['requests']
                              if r['op'] == 1 and r['event_id'] == manual_ack['event_id'])
        assert manual_ack['saved_before_ack']
        if fps:
            assert manual_requested < deadline, (manual_requested, deadline)
            assert manual_request['at'] < deadline, (manual_request['at'], deadline)
        assert station.records.summary()['total'] == len(PRODUCTS) + 1
        assert station.records.confirmations.pending() is None
        assert station.records.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        history = station.records.confirmations.history()
        assert len(history) == len(PRODUCTS) + 1
        assert all(h['status'] == 'ACKNOWLEDGED' for h in history)
        final = server.snapshot()
        state = station.state()
        assert final['queue_depth'] == 0 and not final['failures']
        assert not station.error and bridge.transport.reconnects == 0
        assert bridge.transport.total_received_bytes == final['sent_bytes']
        assert bridge.transport.requests_sent == len(final['requests'])
        assert final['received_bytes'] == 16 * len(final['requests'])
        assert len(final['acks']) == station.captures
        assert len({a['event_id'] for a in final['acks']}) == len(final['acks'])
        result = dict(passed=True, preview_rate_fps=fps, loopback_port=server.port,
                      idle=dict(requested_seconds=IDLE_SECONDS, elapsed_seconds=idle_end-idle_start,
                                captures=len(idle_captures), status_requests=len(idle_stats),
                                configure_requests=sum(r['op'] == 5 for r in idle['requests']),
                                request_count=len(idle['requests']), response_bytes=idle['sent_bytes'],
                                frame_payload_bytes=len(idle_captures)*FRAME_BYTES,
                                ordinary_start_gaps_seconds=gaps, deferred_polls=deferred),
                      automatic_events=automatic, queue_test_seconds=automatic[-1]['ack_at']-queue_start,
                      manual=dict(event_id=manual_ack['event_id'], requested_at=manual_requested,
                                  capture_started_at=manual_request['at'], ordinary_deadline=deadline,
                                  bypass_verified=bool(fps), saved_before_ack=True),
                      totals=dict(requests=bridge.transport.requests_sent,
                                  requests_by_op=dict(Counter(r['op'] for r in final['requests'])),
                                  client_received_bytes=bridge.transport.total_received_bytes,
                                  server_sent_bytes=final['sent_bytes'], client_request_bytes=final['received_bytes'],
                                  captures=station.captures, archived=len(PRODUCTS)+1,
                                  acked=len(final['acks']), reconnects=bridge.transport.reconnects),
                      preview_policy=state['preview_policy'], all_headers_and_pixels_crc_validated=True,
                      sqlite_integrity_check='ok', all_saved_events_committed_before_ack=True,
                      pending_confirmation=None, all_request_log=final['requests'], all_ack_log=final['acks'])
        write_json(directory / 'result.json', result)
        return result
    finally:
        station.action(dict(op='pause'))
        station.exit = True
        station.worker.join(4)
        bridge.close()
        server.close()
        station.records.db.close()
        assert not station.worker.is_alive()


def main():
    report_root = ROOT / 'reports/v148/preview_tcp_load'
    run = report_root / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir(parents=True)
    summary = dict(passed=False, started_utc=datetime.now(timezone.utc).isoformat(),
                   run_directory=str(run), scope='Real loopback TCP protocol and production Station receiver integration.',
                   limitations=['No physical board, HDMI stream, cable or link bandwidth is measured.',
                                'Sender pixels and event decisions are fixtures, not an FPGA detector evaluation.',
                                'Descriptor-CRC verified flag is a sender declaration; actual header and pixel CRCs are checked by EventTCP.',
                                'Short windows exercise scheduling and byte accounting; they do not establish sustained real-board throughput.'],
                   source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                  for name in ('host/workstation.py','host/preview_policy.py','host/tcp_transport.py',
                                               'scripts/test_preview_tcp_load.py')}, cases=[])
    try:
        for fps in (2, 5, 0):
            summary['cases'].append(run_case(run / f'rate_{fps}', fps))
        a, b, c = summary['cases']
        assert a['idle']['captures'] < b['idle']['captures'] <= c['idle']['captures']
        baseline = c['idle']['response_bytes']
        summary['comparison'] = dict(
            idle_response_bytes={str(r['preview_rate_fps']):r['idle']['response_bytes'] for r in summary['cases']},
            idle_captures={str(r['preview_rate_fps']):r['idle']['captures'] for r in summary['cases']},
            response_byte_reduction_vs_unlimited_percent={str(r['preview_rate_fps']):100*(1-r['idle']['response_bytes']/baseline) for r in (a,b)},
            identical_product_ids_saved_and_acked=list(PRODUCTS),
            all_modes_archived_three_automatic_plus_one_manual=True)
        summary['passed'] = True
    except Exception:
        summary['error'] = traceback.format_exc()
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(run / 'summary.json', summary)
        write_json(report_root / 'summary.json', summary)
    print(json.dumps(dict(passed=True, comparison=summary['comparison'],
                          summary=str(report_root/'summary.json')), ensure_ascii=False))


if __name__ == '__main__':
    main()
