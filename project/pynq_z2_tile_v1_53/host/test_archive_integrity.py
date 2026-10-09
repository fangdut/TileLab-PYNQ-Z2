"""Isolated archive fixtures: failures must preserve pixels, metadata and notes."""
from pathlib import Path
import unittest,tempfile,json,hashlib,threading,urllib.request,urllib.error,os,io
from unittest.mock import patch
from PIL import Image
from archive_integrity import EvidenceReadError,read_verified_image,MAX_PNG_BYTES
from workstation import Records,Station,ThreadingHTTPServer,handler
import test_workstation as fixtures

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_archive_integrity_');self.root=Path(self.tmp.name)
        self.records=Records(self.root);self.frame,self.image,self.mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet())
        self.key=self.records.save(self.frame,self.image,self.mask,'isolated_protocol_test');self.records.update(self.key,'needs_recheck','Preserve this note')
    def tearDown(self):self.records.db.close();self.tmp.cleanup()
    def test_original_and_mask_return_verified_bytes(self):
        for mask,data in ((False,self.image),(True,self.mask)):
            returned,digest=self.records.read_image(self.key,mask);self.assertEqual(returned,data);self.assertEqual(digest,hashlib.sha256(data).hexdigest())
    def test_decodable_trailing_corruption_is_rejected(self):
        for mask,data in ((False,self.image),(True,self.mask)):
            p=self.records.file(self.key,mask);corrupt=data+b'UNTRUSTED_TRAILING_BYTES';p.write_bytes(corrupt);Image.open(io.BytesIO(corrupt)).load()
            with self.assertRaises(EvidenceReadError):self.records.read_image(self.key,mask)
            self.assertEqual(p.read_bytes(),corrupt);p.write_bytes(data)
    def test_single_byte_damage_is_rejected(self):
        p=self.records.file(self.key);bad=bytearray(self.image);bad[len(bad)//2]^=1;p.write_bytes(bad)
        with self.assertRaises(EvidenceReadError):self.records.read_image(self.key)
    def test_missing_file_has_explicit_read_error(self):
        p=self.records.file(self.key);p.rename(p.with_suffix('.kept'))
        with self.assertRaises(EvidenceReadError) as e:self.records.read_image(self.key)
        self.assertEqual(e.exception.code,'ARCHIVE_IMAGE_UNAVAILABLE');self.assertEqual(e.exception.http_status,503)
    def test_overlarge_file_read_is_bounded(self):
        p=self.records.file(self.key)
        with p.open('wb') as f:f.truncate(MAX_PNG_BYTES+1)
        with self.assertRaises(EvidenceReadError) as e:self.records.read_image(self.key)
        self.assertEqual(e.exception.code,'ARCHIVE_IMAGE_TOO_LARGE')
    def test_invalid_or_missing_stored_hash_is_not_trusted(self):
        p=self.records.file(self.key)
        for expected in (None,'','A'*64,'g'*64,True,[], 'a'*63):
            with self.assertRaises(EvidenceReadError):read_verified_image(p,expected)
    def test_bad_metadata_is_explicit(self):
        self.records.db.execute('UPDATE events SET payload=? WHERE id=?',('[]',self.key));self.records.db.commit()
        with self.assertRaises(EvidenceReadError) as e:self.records.read_image(self.key)
        self.assertEqual(e.exception.code,'ARCHIVE_METADATA_INVALID')
    def test_invalid_key_cannot_be_read(self):
        for key in ('../bad','','a/b','a'*129,None):
            with self.assertRaises(ValueError):self.records.read_image(key)
    def test_review_rechecks_both_images_without_mutating_existing_notes(self):
        for mask,data in ((False,self.image),(True,self.mask)):
            p=self.records.file(self.key,mask);p.write_bytes(data+b'changed after opening review')
            with self.assertRaises(EvidenceReadError):self.records.review(self.key,'confirmed_crack','Should not commit',self.records.get(self.key)['review_revision'])
            row=self.records.all()[0];self.assertEqual(row['review'],'needs_recheck');self.assertEqual(row['note'],'Preserve this note')
            self.assertTrue(p.read_bytes().endswith(b'changed after opening review'));p.write_bytes(data)
    def test_successful_review_does_not_reencode_images(self):
        self.records.review(self.key,'false_alarm','Reviewed verified files',self.records.get(self.key)['review_revision'])
        self.assertEqual(self.records.file(self.key).read_bytes(),self.image);self.assertEqual(self.records.file(self.key,True).read_bytes(),self.mask)
        self.assertEqual(self.records.all()[0]['review'],'false_alarm')
    def test_path_change_after_hash_does_not_change_returned_bytes(self):
        p=self.records.file(self.key);real_sha=hashlib.sha256
        def digest(data):
            result=real_sha(data);p.write_bytes(b'replacement after verification');return result
        with patch('archive_integrity.hashlib.sha256',side_effect=digest):data,value=self.records.read_image(self.key)
        self.assertEqual(data,self.image);self.assertEqual(value,real_sha(self.image).hexdigest());self.assertNotEqual(data,p.read_bytes())

class ArchiveHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_archive_http_');self.root=Path(self.tmp.name);self.station=Station(self.root,fixtures.DummyBridge())
        f,self.image,self.mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet());self.key=self.station.records.save(f,self.image,self.mask,'isolated_protocol_test')
        self.station.records.update(self.key,'needs_recheck','Keep original note')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.station));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.station.exit=True;self.station.worker.join(2);self.server.shutdown();self.server.server_close();self.station.records.db.close();self.tmp.cleanup()
    def get(self,mask=False):return urllib.request.urlopen(self.base+f'/api/image?id={self.key}&mask={int(mask)}')
    def test_success_response_binds_bytes_to_digest_and_disables_cache(self):
        for mask,data in ((False,self.image),(True,self.mask)):
            with self.get(mask) as response:
                self.assertEqual(response.read(),data);self.assertEqual(response.headers['X-Archive-Integrity'],'sha256-verified')
                self.assertEqual(response.headers['X-Archive-SHA256'],hashlib.sha256(data).hexdigest());self.assertEqual(response.headers['Cache-Control'],'no-store')
    def test_corrupt_original_and_mask_return_error_not_pixels(self):
        for mask,data in ((False,self.image),(True,self.mask)):
            p=self.station.records.file(self.key,mask);p.write_bytes(data+b'extra')
            with self.assertRaises(urllib.error.HTTPError) as error:self.get(mask)
            self.assertEqual(error.exception.code,409);body=json.load(error.exception);self.assertEqual(body['code'],'ARCHIVE_INTEGRITY_FAILED')
            self.assertEqual(p.read_bytes(),data+b'extra');p.write_bytes(data)
    def test_missing_file_returns_json_not_a_broken_connection(self):
        p=self.station.records.file(self.key);p.rename(p.with_suffix('.kept'))
        with self.assertRaises(urllib.error.HTTPError) as e:self.get()
        self.assertEqual(e.exception.code,503);self.assertEqual(json.load(e.exception)['code'],'ARCHIVE_IMAGE_UNAVAILABLE')
    def test_submission_rejects_damage_after_successful_open(self):
        self.get().close();self.get(True).close();p=self.station.records.file(self.key,True);p.write_bytes(self.mask+b'after open')
        req=urllib.request.Request(self.base+'/api/review',data=json.dumps(dict(id=self.key,review='confirmed_crack',note='Must not commit',expected_revision=self.station.records.get(self.key)['review_revision'])).encode(),headers={'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,409);row=self.station.records.all()[0];self.assertEqual(row['note'],'Keep original note');self.assertEqual(row['review'],'needs_recheck')
    def test_actual_windows_exclusive_lock_is_recoverable(self):
        if os.name!='nt':self.skipTest('Windows sharing violation')
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=k.CreateFileW(str(self.station.records.file(self.key)),0x80000000,0,None,3,0,None);self.assertNotEqual(handle,wintypes.HANDLE(-1).value)
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:self.get()
            self.assertEqual(e.exception.code,503);self.assertEqual(json.load(e.exception)['code'],'ARCHIVE_IMAGE_UNAVAILABLE')
        finally:k.CloseHandle(handle)
        with self.get() as response:self.assertEqual(response.read(),self.image)
    def test_http_sends_verified_snapshot_even_if_path_changes_after_check(self):
        p=self.station.records.file(self.key);real_sha=hashlib.sha256
        def digest(data):
            value=real_sha(data);p.write_bytes(b'another file now');return value
        with patch('archive_integrity.hashlib.sha256',side_effect=digest):
            with self.get() as response:self.assertEqual(response.read(),self.image);self.assertEqual(response.headers['X-Archive-SHA256'],real_sha(self.image).hexdigest())
    def test_live_frame_route_does_not_use_archive_checks(self):
        with self.station.lock:self.station.live_frames['test_live']=(self.image,self.mask)
        with urllib.request.urlopen(self.base+'/api/image?frame=test_live') as response:
            self.assertEqual(response.read(),self.image);self.assertIsNone(response.headers.get('X-Archive-Integrity'))

if __name__=='__main__':unittest.main(verbosity=2)
