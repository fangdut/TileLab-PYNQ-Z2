import unittest,json,threading,urllib.request,urllib.error,hashlib,shutil,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from review_server import Store,handler,ROOT

class ReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=ROOT/'reports'/('review_test_'+str(time.time_ns()));cls.temp.mkdir()
        (cls.temp/'data/synthetic').mkdir(parents=True)
        manifest=json.loads((ROOT/'data/manifest.json').read_text());manifest['items']=manifest['items'][:2]
        (cls.temp/'data/manifest.json').write_text(json.dumps(manifest))
        for r in manifest['items']:shutil.copy2(ROOT/'data'/r['image'],cls.temp/'data'/r['image'])
        (cls.temp/'data/hdmi_stationary_SYNTHETIC_720p60.mp4').write_bytes(b'0123456789abcdef')
        cls.store=Store(cls.temp);cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler(cls.store))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,data=None,headers=None):
        req=urllib.request.Request(self.url+path,json.dumps(data).encode() if data else None,headers or {})
        return urllib.request.urlopen(req,timeout=3)
    def test_01_explicit_offline(self):
        j=json.load(self.request('/api/state'));self.assertFalse(j['board_connected']);self.assertEqual(j['mode'],'OFFLINE_REFERENCE')
    def test_02_capture_and_deduplicate(self):
        self.assertFalse(json.load(self.request('/api/capture',{'id':'tile_000'}))['saved'])
        for _ in range(3):self.assertTrue(json.load(self.request('/api/capture',{'id':'tile_001'}))['saved'])
        self.assertEqual(len(self.store.reviews),1)
        self.assertEqual(hashlib.sha256((self.temp/'data/synthetic/tile_001.png').read_bytes()).hexdigest(),self.store.reviews['tile_001']['image_sha256'])
    def test_03_review_persistence(self):
        self.request('/api/capture',{'id':'tile_001'}).close()
        self.request('/api/review',{'id':'tile_001','review':'false_alarm','note':'这是软件功能测试'}).close()
        self.assertEqual(Store(self.temp).reviews['tile_001']['note'],'这是软件功能测试')
        self.assertEqual(Store(self.temp).reviews['tile_001']['review'],'false_alarm')
    def test_04_reject_invalid(self):
        for path,data in [('/api/capture',{'id':'../../README.md'}),('/api/review',{'id':'tile_001','review':'good'})]:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request(path,data)
            self.assertEqual(e.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/capture',{'id':'tile_001'},{'Origin':'https://unrelated.invalid'})
        self.assertEqual(e.exception.code,403)
    def test_05_range_video(self):
        r=self.request('/video?name=hdmi_stationary_SYNTHETIC_720p60.mp4',headers={'Range':'bytes=2-5'})
        self.assertEqual(r.status,206);self.assertEqual(r.read(),b'2345')
    def test_06_export(self):
        j=json.load(self.request('/api/export'));self.assertEqual(j['origin'],'OFFLINE_REFERENCE')
        self.assertEqual(j['records'][0]['frame_id'],'tile_001')

if __name__=='__main__':unittest.main(verbosity=2)
