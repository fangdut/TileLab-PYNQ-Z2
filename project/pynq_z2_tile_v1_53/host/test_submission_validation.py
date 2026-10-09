import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from workstation import handler

class SubmissionValidation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'reports/v153/real_board').mkdir(parents=True)
        (self.root/'reports/v148').mkdir()
        (self.root/'reports/v148/validation_summary.json').write_text('{"version":"V1.48"}')
        (self.root/'host').mkdir()
        (self.root/'host/benchmark.html').write_bytes((Path(__file__).parent/'benchmark.html').read_bytes())
        self.report=self.root/'reports/v153/final_validation_summary.json'
        self.report.write_text('{"version":"V1.53","engineering_acceptance":true}')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(SimpleNamespace(root=self.root)))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def get(self,path):return urllib.request.urlopen(self.url+path,timeout=3)
    def error(self,path,code):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.get(path)
        self.assertEqual(caught.exception.code,code)
        caught.exception.close()
    def test_current_report_no_historical_substitution(self):
        with self.get('/api/benchmark') as r:data=json.load(r)
        self.assertEqual(data['version'],'V1.53');self.assertEqual(data['delivery_release'],'1.53.1')
    def test_missing_report_is_unavailable_even_with_old_report(self):
        self.report.unlink();self.error('/api/benchmark',503)
    def test_wrong_version_rejected(self):
        self.report.write_text('{"version":"V1.48"}');self.error('/api/benchmark',503)
    def test_non_object_report_rejected(self):
        self.report.write_text('[]');self.error('/api/benchmark',503)
    def test_actual_current_capture_used(self):
        image=b'current-capture-path-test'
        (self.root/'reports/v153/real_board/real_000_original.png').write_bytes(image)
        with self.get('/api/benchmark-image?id=0') as r:self.assertEqual(r.read(),image)
        self.error('/api/benchmark-image?id=-1',404)
    def test_historical_missing_illustration_is_gone(self):self.error('/weak-comparison.png',410)
    def test_page_explains_current_scope_and_async_cache(self):
        with self.get('/benchmark') as r:page=r.read().decode()
        for term in ('V1.53.1','后台线程','V1.52','1.92%','24 张仅 1 张'):self.assertIn(term,page)
        self.assertNotIn('reports/v148',page)
if __name__=='__main__':unittest.main(verbosity=2)
