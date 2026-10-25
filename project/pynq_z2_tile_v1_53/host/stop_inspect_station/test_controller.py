"""Workflow interlock tests with an explicit fake backend, not FPGA evidence."""
from pathlib import Path
import tempfile
import threading
import unittest
from controller import Station, sha


class FakeBackend:
    def __init__(self):
        self.alarm = 0
        self.disconnected = False
        self.started = threading.Event()
        self.continue_inference = threading.Event()
        self.continue_inference.set()

    def check(self):
        if self.disconnected:
            raise ConnectionError('Injected board connection loss')
        return dict(boot_identity=123)

    def inspect(self, image, folder):
        self.started.set()
        if not self.continue_inference.wait(3):
            raise TimeoutError('Injected inspection timeout')
        return dict(pl_image_alarm=self.alarm, result_sha256='fixture-only',
                    boot_identity=123, pl_frame_sequence=1)


class Interlocks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root/'test.png'
        self.image.write_bytes(b'fake backend fixture, not a photograph')
        self.catalog = [dict(id='fixture', file=str(self.image), sha256=sha(self.image),
                             name='Fake backend fixture', source_url='https://example.invalid')]
        self.backend = FakeBackend()
        self.station = Station(self.backend, self.catalog, self.root/'records')

    def tearDown(self):
        self.backend.continue_inference.set()
        if self.station.worker:
            self.station.worker.join(5)
        self.temp.cleanup()

    def act(self, op, **values):
        s = self.station.state()
        return self.station.action(dict(session=s['session'], revision=s['revision'], op=op, **values))

    def inspect(self, alarm=0):
        self.backend.alarm = alarm
        self.act('load', sample_id='fixture')
        self.act('inspect', input_held_confirmed=True)
        self.station.worker.join(5)
        return self.station.state()

    def confirm(self, op):
        state = self.station.state()
        result_id = state['cycle']['result']['id']
        self.act(op, operator_confirmed=True, result_id=result_id)
        self.station.worker.join(5)
        return self.station.state()

    def test_good_never_releases_before_confirmation(self):
        state = self.inspect()
        self.assertEqual(state['phase'], 'GOOD_HOLD')
        self.assertTrue(state['stop_requested'])
        self.assertFalse(state['logical_release_requested'])
        with self.assertRaises(ValueError):
            self.act('release', result_id=state['cycle']['result']['id'])
        self.assertEqual(self.confirm('release')['phase'], 'RELEASED')

    def test_defect_cannot_be_released_as_good(self):
        self.inspect(1)
        with self.assertRaises(ValueError):
            self.act('release', operator_confirmed=True, result_id=self.station.cycle['result']['id'])
        self.assertEqual(self.confirm('segregate')['phase'], 'SEGREGATED')
        self.assertEqual(self.station.counts['released'], 0)

    def test_board_loss_at_confirmation_clears_old_good_result(self):
        self.inspect()
        self.backend.disconnected = True
        state = self.confirm('release')
        self.assertEqual(state['phase'], 'FAULT')
        self.assertTrue(state['stop_requested'])
        self.assertIsNone(state['cycle']['result'])
        self.assertEqual(state['counts']['released'], 0)
        self.act('reset_fault', operator_confirmed=True)
        self.assertIsNone(self.station.cycle)

    def test_old_result_and_old_revision_are_rejected(self):
        state = self.inspect()
        with self.assertRaises(ValueError):
            self.act('release', operator_confirmed=True, result_id='wrong-cycle-result')
        old = dict(op='release', session=state['session'], revision=state['revision'],
                   operator_confirmed=True, result_id=state['cycle']['result']['id'])
        self.station.action(old)
        self.station.worker.join(5)
        with self.assertRaises(ValueError):
            self.station.action(old)

    def test_input_must_remain_fixed_during_inspection(self):
        self.backend.continue_inference.clear()
        self.act('load', sample_id='fixture')
        self.act('inspect', input_held_confirmed=True)
        self.assertTrue(self.backend.started.wait(2))
        folder = self.root/'records/cycles'/self.station.cycle['id']
        (folder/'source.png').write_bytes(b'changed input')
        with self.assertRaises(ValueError):
            self.act('load', sample_id='fixture')
        self.backend.continue_inference.set()
        self.station.worker.join(5)
        self.assertEqual(self.station.phase, 'FAULT')
        self.assertIsNone(self.station.cycle['result'])

    def test_concurrent_duplicate_inspect_starts_only_once(self):
        self.act('load', sample_id='fixture')
        s = self.station.state()
        body = dict(op='inspect', session=s['session'], revision=s['revision'], input_held_confirmed=True)
        results = []
        def invoke():
            try:
                self.station.action(body)
                results.append(True)
            except ValueError:
                results.append(False)
        a = threading.Thread(target=invoke)
        b = threading.Thread(target=invoke)
        a.start(); b.start(); a.join(); b.join()
        self.station.worker.join(5)
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.station.counts['inspected'], 1)

    def test_new_session_never_resumes_old_good_result(self):
        old = self.inspect()
        new = Station(self.backend, self.catalog, self.root/'records')
        self.assertEqual(new.phase, 'READY')
        self.assertIsNone(new.cycle)
        with self.assertRaises(ValueError):
            new.action(dict(op='release', session=old['session'], revision=0,
                            operator_confirmed=True, result_id=old['cycle']['result']['id']))

    def test_corrupt_catalog_image_cannot_be_loaded(self):
        self.image.write_bytes(b'corrupted')
        with self.assertRaises(ValueError):
            self.act('load', sample_id='fixture')
        self.assertIsNone(self.station.cycle)

    def test_import_preserves_original_png_and_jpeg_bytes(self):
        from PIL import Image
        import io
        for format in ['PNG', 'JPEG']:
            data = io.BytesIO()
            Image.new('RGB', (13, 17), (127, 80, 60)).save(data, format=format)
            raw = data.getvalue()
            imported = self.station.add_image(raw, 'fixture.'+format.lower())
            row = self.station.catalog[imported['sample_id']]
            self.assertEqual(Path(row['file']).read_bytes(), raw)
            self.assertFalse(row['accuracy_prevalidated'])

    def test_import_rejects_unsupported_format_and_oversized_dimensions(self):
        from PIL import Image
        import io
        for size, format in [((1025, 5), 'PNG'), ((5, 5), 'GIF')]:
            data = io.BytesIO()
            Image.new('RGB', size).save(data, format=format)
            with self.assertRaises(ValueError):
                self.station.add_image(data.getvalue(), 'fixture')


if __name__ == '__main__':
    unittest.main(verbosity=2)
