# SPDX-License-Identifier: MIT
import io,unittest
from urllib.error import URLError
from unittest.mock import patch
from server import StationAPI


class FakeOpener:
    def __init__(self):self.calls=0
    def open(self,request,timeout):
        self.calls+=1
        if self.calls==1:raise URLError('temporary loopback connection timeout')
        return io.BytesIO(b'{"phase":"READY"}')


class APITests(unittest.TestCase):
    def test_temporary_state_read_failure_recovers(self):
        api=StationAPI('http://127.0.0.1:8793');api.opener=FakeOpener()
        with patch('server.time.sleep'):
            self.assertEqual(api.state()['phase'],'READY')
        self.assertEqual(api.opener.calls,2)

    def test_post_is_not_replayed(self):
        api=StationAPI('http://127.0.0.1:8793');api.opener=FakeOpener()
        with self.assertRaises(URLError):api.request('/api/action',b'{"op":"inspect"}')
        self.assertEqual(api.opener.calls,1)

    def test_upload_is_not_replayed(self):
        api=StationAPI('http://127.0.0.1:8793');api.opener=FakeOpener()
        with self.assertRaises(URLError):api.request('/api/upload',b'image')
        self.assertEqual(api.opener.calls,1)


if __name__=='__main__':unittest.main()
