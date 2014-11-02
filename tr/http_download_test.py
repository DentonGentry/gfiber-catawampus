#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for http_download.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

from collections import namedtuple  # pylint:disable=g-importing-member
import shutil
import tempfile
from wvtest import unittest

import google3
from curtain import digest
import tornado.testing
import tornado.web
import http_download


mock_http_clients = []


class MockHttpClient(object):
  def __init__(self, io_loop=None):
    self.did_fetch = False
    self.request = None
    self.callback = None
    mock_http_clients.append(self)

  def fetch(self, request, callback):
    self.did_fetch = True
    self.request = request
    self.callback = callback


class MockHttpResponse(object):
  def __init__(self, errorcode):
    self.error = namedtuple('error', 'code')
    self.error.code = errorcode
    self.headers = []


class MockIoloop(object):
  def __init__(self):
    self.time = None
    self.callback = None
    self.started = False
    self.stopped = False

  def add_timeout(self, time, callback):
    self.time = time
    self.callback = callback

  def start(self):
    self.started = True

  def stop(self):
    self.stopped = True


class MockTempFileIOError(object):
  def __init__(self, delete, dir):  # pylint:disable=redefined-builtin
    self.delete = delete
    self.dir = dir
    self.name = 'MockTempFileIOError'

  def close(self):
    raise IOError('close')

  def flush(self):
    raise IOError('flush')

  def seek(self, offset):
    pass

  def truncate(self, siz):
    pass

  def write(self, buf):
    # Note that you'll see a traceback in the test output from this line.
    # That is normal, we're testing the handling of the IOError.
    raise IOError('write')


class DigestAuthHandler(digest.DigestAuthMixin, tornado.web.RequestHandler):
  def getcredentials(self, username):
    credentials = {'auth_username': 'user', 'auth_password': 'pass'}
    if username == credentials['auth_username']:
      return credentials

  def get(self):
    # Digest authentication handler
    if self.get_authenticated_user(self.getcredentials, 'Authusers'):
      print 'DigestAuthHandler'
      self.write('DigestHandler')
      return self.set_status(200)


class SimpleHandler(tornado.web.RequestHandler):
  def get(self):
    self.write('SimpleHandler')
    return self.set_status(200)


class HttpDownloadTest(tornado.testing.AsyncHTTPTestCase, unittest.TestCase):
  """tests for http_download.py HttpDownload."""

  def get_app(self):
    return tornado.web.Application(
        [('/digest', DigestAuthHandler),
         ('/simple', SimpleHandler)])

  def setUp(self):
    super(HttpDownloadTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.dl_cb_faultcode = None
    self.dl_cb_faultstring = None
    self.dl_cb_filename = None
    self.old_httpclient = http_download.HTTPCLIENT
    self.old_tempfile = http_download.TEMPFILE
    self.old_percent_complete_file = http_download.PERCENT_COMPLETE_FILE
    http_download.PERCENT_COMPLETE_FILE = None
    del mock_http_clients[:]
    tornado.httpclient.AsyncHTTPClient.configure(
        'tornado.curl_httpclient.CurlAsyncHTTPClient')

  def tearDown(self):
    super(HttpDownloadTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    del mock_http_clients[:]
    http_download.HTTPCLIENT = self.old_httpclient
    http_download.PERCENT_COMPLETE_FILE = self.old_percent_complete_file
    http_download.TEMPFILE = self.old_tempfile

  def testDigest(self):
    expected = '6629fae49393a05397450978507c4ef1'
    actual = http_download.calc_http_digest(
        'GET',
        '/dir/index.html',
        'auth',
        nonce='dcd98b7102dd2f0e8b11d0f600bfb0c093',
        cnonce='0a4f113b',
        nc='00000001',
        username='Mufasa',
        password='Circle Of Life',
        realm='testrealm@host.com')
    self.assertEqual(expected, actual)

  def downloadCallback(self, faultcode, faultstring, fileobj):
    self.dl_cb_faultcode = faultcode
    self.dl_cb_faultstring = faultstring
    if fileobj:
      self.dl_cb_filename = fileobj.name
    self.stop()

  def testFetchMocked(self):
    """Test arguments to a mocked HttpClient."""
    http_download.HTTPCLIENT = MockHttpClient
    ioloop = MockIoloop()
    username = 'uname'
    password = 'pword'
    url = 'scheme://host:port/'
    dl = http_download.HttpDownload(url, username=username, password=password,
                                    download_complete_cb=self.downloadCallback,
                                    ioloop=ioloop)
    dl.fetch()
    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.did_fetch)
    self.assertTrue(ht.request is not None)
    self.assertEqual(ht.request.auth_username, username)
    self.assertEqual(ht.request.auth_password, password)
    self.assertEqual(ht.request.url, url)

    resp = MockHttpResponse(418)
    ht.callback(resp)
    self.assertEqual(self.dl_cb_faultcode, 9010)  # DOWNLOAD_FAILED
    self.assertTrue(self.dl_cb_faultstring)
    self.assertFalse(self.dl_cb_filename)

  def testFetchFerRealz(self):
    """Test a real HTTP fetch to a local server."""
    url = self.get_url('/simple')
    dl = http_download.HttpDownload(url, username=None, password=None,
                                    download_complete_cb=self.downloadCallback,
                                    ioloop=self.io_loop)
    dl.fetch()
    self.wait(timeout=1)
    self.assertTrue(self.dl_cb_filename)
    with open(self.dl_cb_filename) as f:
      self.assertEqual(f.read(), 'SimpleHandler')

  def testFetchDigestAuth(self):
    """Fetch from a local server requiring digest auth."""
    url = self.get_url('/digest')
    dl = http_download.HttpDownload(url, username='user', password='pass',
                                    download_complete_cb=self.downloadCallback,
                                    ioloop=self.io_loop)
    dl.fetch()
    self.wait(timeout=1)
    self.assertTrue(self.dl_cb_filename)
    with open(self.dl_cb_filename) as f:
      self.assertEqual(f.read(), 'DigestHandler')

  def testFetchDiskFull(self):
    """Fetch from a local server requiring digest auth."""
    http_download.TEMPFILE = MockTempFileIOError
    url = self.get_url('/simple')
    dl = http_download.HttpDownload(url, username=None, password=None,
                                    download_complete_cb=self.downloadCallback,
                                    ioloop=self.io_loop)
    dl.fetch()
    self.wait(timeout=1)
    self.assertEqual(self.dl_cb_faultcode, 9010)  # DOWNLOAD_FAILED

  def testMainDownload(self):
    """Check that main() still works."""
    http_download.HTTPCLIENT = MockHttpClient
    ioloop = MockIoloop()
    url = 'http://www.google.com'
    username = 'user'
    password = 'pass'
    # This won't actually fetch www.google.com, httpclient is mocked.
    http_download.main_dl_start(url=url, username=username,
                                password=password, ioloop=ioloop)
    self.assertTrue(ioloop.started)
    self.assertFalse(ioloop.stopped)

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.did_fetch)
    self.assertTrue(ht.request is not None)
    self.assertEqual(ht.request.auth_username, username)
    self.assertEqual(ht.request.auth_password, password)
    self.assertEqual(ht.request.url, url)

    resp = MockHttpResponse(418)
    ht.callback(resp)
    self.assertTrue(ioloop.stopped)


if __name__ == '__main__':
  unittest.main()
