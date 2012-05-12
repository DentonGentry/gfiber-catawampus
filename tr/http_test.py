#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for http.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import mox
import os
import shutil
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

import google3
import dm_root
import tornado.httpclient
import tornado.ioloop
import tornado.testing

import api
import cwmp_session
import cwmpdate
import download
import http


mock_http_client_stop = None
mock_http_clients = []
SOAPNS = '{http://schemas.xmlsoap.org/soap/envelope/}'
CWMPNS = '{urn:dslforum-org:cwmp-1-2}'


class MockHttpClient(object):
  def __init__(self, **kwargs):
    self.ResetMock()
    mock_http_clients.append(self)

  def ResetMock(self):
    self.req = None
    self.fetch_called = False

  def fetch(self, req, callback):
    self.fetch_req = req
    self.fetch_callback = callback
    self.fetch_called = True
    mock_http_client_stop()


class HttpTest(tornado.testing.AsyncTestCase):
  def setUp(self):
    super(HttpTest, self).setUp()
    self.old_time = time.time
    self.advance_time = 0
    self.old_HTTPCLIENT = cwmp_session.HTTPCLIENT
    cwmp_session.HTTPCLIENT = MockHttpClient
    global mock_http_client_stop
    mock_http_client_stop = self.stop
    self.removedirs = list()
    self.removefiles = list()
    del mock_http_clients[:]

  def tearDown(self):
    super(HttpTest, self).tearDown()
    time.time = self.old_time
    cwmp_session.HTTPCLIENT = self.old_HTTPCLIENT
    for d in self.removedirs:
      shutil.rmtree(d)
    for f in self.removefiles:
      os.remove(f)
    del mock_http_clients[:]

  def advanceTime(self):
    return self.old_time() + self.advance_time

  def getCpe(self):
    dm_root.PLATFORMDIR = '../platform'
    root = dm_root.DeviceModelRoot(self.io_loop, 'fakecpe')
    cpe = api.CPE(root)
    dldir = tempfile.mkdtemp()
    self.removedirs.append(dldir)
    cfdir = tempfile.mkdtemp()
    self.removedirs.append(cfdir)
    cpe.download_manager.SetDirectories(config_dir=cfdir, download_dir=dldir)
    acsfile = tempfile.NamedTemporaryFile(delete=False)
    self.removefiles.append(acsfile.name)
    acsfile.write('http://example.com/cwmp')
    acsfile.close()
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path='/ping/http_test',
                              acs=None, acs_url_file=acsfile.name,
                              cpe=cpe, cpe_listener=False, ioloop=self.io_loop)
    return cpe_machine

  def testMaxEnvelopes(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    envelope = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/MaxEnvelopes')
    self.assertTrue(envelope is not None)
    self.assertEqual(envelope.text, '1')

  def testCurrentTime(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

  def testLookupDevIP6(self):
    http.PROC_IF_INET6 = 'testdata/http/if_inet6'
    cpe_machine = self.getCpe()
    self.assertEqual(cpe_machine.LookupDevIP6('eth0'),
                     '11:2233:4455:6677:8899:aabb:ccdd:eeff')
    self.assertEqual(cpe_machine.LookupDevIP6('foo0'), 0)

  def testRetryCount(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait(timeout=20)

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '0')

    # Fail the first request
    httpresp = tornado.httpclient.HTTPResponse(ht.fetch_req, 404)
    ht.fetch_callback(httpresp)

    self.advance_time += 10
    self.wait(timeout=20)
    self.assertEqual(len(mock_http_clients), 2)
    ht = mock_http_clients[1]

    root = ET.fromstring(ht.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '1')

  def testNewPingSession(self):
    cpe_machine = self.getCpe()
    cpe_machine.previous_ping_time = 0

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    ioloop_mock = m.CreateMock(tornado.ioloop.IOLoop)
    m.StubOutWithMock(cpe_machine, "_NewSession")
    m.StubOutWithMock(time, "time")
    
    # First call to _NewSession should get the time and trigger a new session
    time.time().AndReturn(1000)
    cpe_machine._NewSession(mox.IsA(str))

    # Second call to _NewSession should queue a session
    time.time().AndReturn(1001)
    ioloop_mock.add_timeout(mox.IsA(int), mox.IgnoreArg()).AndReturn(1)

    # Third call should get the time and then not do anything
    # since a session is queued.
    time.time().AndReturn(1001)

    # And the call to _NewTimeoutSession should call through to
    # NewPingSession, and start a new session
    time.time().AndReturn(1000 + cpe_machine.rate_limit_seconds)
    ioloop_mock.add_timeout(mox.IsA(int), mox.IgnoreArg()).AndReturn(2)
    cpe_machine.ioloop = ioloop_mock
    m.ReplayAll()

    # Real test starts here.
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewTimeoutPingSession()
    
    # Verify everything was called correctly.
    m.VerifyAll()


class TestManagementServer(object):
  ConnectionRequestUsername = 'username'
  ConnectionRequestPassword = 'password'


class PingTest(tornado.testing.AsyncHTTPTestCase):
  def ping_callback(self):
    self.ping_calledback = True

  def get_app(self):
    return tornado.web.Application(
        [('/', http.PingHandler, dict(cpe_ms=TestManagementServer(),
                                      callback=self.ping_callback))])

  def test_ping(self):
    self.ping_calledback = False
    self.http_client.fetch(self.get_url('/'), self.stop)
    response = self.wait()
    self.assertEqual(response.error.code, 401)
    self.assertFalse(self.ping_calledback)
    self.assertTrue(response.body.find('qop'))


if __name__ == '__main__':
  unittest.main()
