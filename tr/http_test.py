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
# pylint: disable-msg=C6409

"""Unit tests for http.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

# pylint: disable-msg=g-bad-import-order,unused-import
import epoll_fix  # this needs to be first, before any tornado imports
# pylint: enable-msg=g-bad-import-order,unused-import

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

import google3

import dm_root
import mox
import tornado.httpclient
import tornado.ioloop
import tornado.testing
import tornado.util
import tornado.web

import api
import cwmpdate
import http
import session


SOAPNS = '{http://schemas.xmlsoap.org/soap/envelope/}'
CWMPNS = '{urn:dslforum-org:cwmp-1-2}'


def GetMonotime():
  """Older tornado doesn't have monotime(); stay compatible."""
  if hasattr(tornado.util, 'monotime_impl'):
    return tornado.util.monotime_impl
  else:
    return time.time


def SetMonotime(func):
  """Older tornado doesn't have monotime(); stay compatible."""
  if hasattr(tornado.util, 'monotime_impl'):
    tornado.util.monotime_impl = func
  else:
    time.time = func


def StubOutMonotime(moxinstance):
  if hasattr(tornado.util, 'monotime_impl'):
    moxinstance.StubOutWithMock(tornado.util, 'monotime_impl')
  else:
    moxinstance.StubOutWithMock(time, 'time')


class WrapHttpClient(object):
  def __init__(self, oldclient, stopfunc, **kwargs):
    self.stopfunc = stopfunc
    self.realclient = oldclient(**kwargs)

  def fetch(self, req, callback):
    print '%s: fetching: %s %s' % (self, req, callback)
    def mycallback(httpresponse):
      print 'WrapHTTP request: finished request for %r' % req.url
      callback(httpresponse)
      self.stopfunc()
    self.realclient.fetch(req, mycallback)

  def close(self):
    self.realclient.close()

  def handle_callback_exception(self, callback):
    self.realclient.handle_callback_exception(callback)


class MockAcsConfig(object):
  def __init__(self, port):
    self.port = port

  def GetAcsUrl(self):
    return 'http://127.0.0.1:%d/cwmp' % self.port

  def AcsAccessAttempt(self, unused_url):
    pass

  def AcsAccessSuccess(self, unused_url):
    pass


class LinearHttpHandler(tornado.web.RequestHandler):
  def initialize(self, callback):
    self.callback = callback

  def _handle(self):
    print 'LinearHttpHandler: got %r request for %r' % (self.request.method,
                                                        self.request.path)
    self.callback(self)

  @tornado.web.asynchronous
  def get(self):
    return self._handle()

  @tornado.web.asynchronous
  def post(self):
    return self._handle()


class HttpTest(tornado.testing.AsyncHTTPTestCase):
  def setUp(self):
    self.old_HTTPCLIENT = session.HTTPCLIENT
    def _WrapWrapper(**kwargs):
      return WrapHttpClient(self.old_HTTPCLIENT, self.stop, **kwargs)
    session.HTTPCLIENT = _WrapWrapper
    self.app = tornado.web.Application(
        [
            ('/cwmp', LinearHttpHandler,
             dict(callback=self.HttpRequestReceived)),
            ('/redir.*', LinearHttpHandler,
             dict(callback=self.HttpRequestReceived)),
        ])
    super(HttpTest, self).setUp()  # calls get_app(), so self.app must exist
    self.requestlog = []
    self.old_monotime = GetMonotime()
    self.advance_time = 0
    self.removedirs = list()
    self.removefiles = list()

  def tearDown(self):
    session.HTTPCLIENT = self.old_HTTPCLIENT
    super(HttpTest, self).tearDown()
    SetMonotime(self.old_monotime)
    for d in self.removedirs:
      shutil.rmtree(d)
    for f in self.removefiles:
      os.remove(f)

  def get_app(self):
    return self.app

  def HttpRequestReceived(self, handler):
    self.requestlog.append(handler)
    self.stop()

  def NextHandler(self):
    while not self.requestlog:
      self.wait()
    return self.requestlog.pop(0)

  def advanceTime(self):
    return 420000.0 + self.advance_time

  def getCpe(self):
    dm_root.PLATFORMDIR = '../platform'
    root = dm_root.DeviceModelRoot(self.io_loop, 'fakecpe', ext_dir=None)
    cpe = api.CPE(root)
    dldir = tempfile.mkdtemp()
    self.removedirs.append(dldir)
    cfdir = tempfile.mkdtemp()
    self.removedirs.append(cfdir)
    cpe.download_manager.SetDirectories(config_dir=cfdir, download_dir=dldir)
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path='/ping/http_test',
                              acs=None, cpe=cpe, cpe_listener=False,
                              acs_config=MockAcsConfig(self.get_http_port()),
                              ioloop=self.io_loop)
    return cpe_machine

  def testMaxEnvelopes(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')

    root = ET.fromstring(h.request.body)
    envelope = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/MaxEnvelopes')
    self.assertTrue(envelope is not None)
    self.assertEqual(envelope.text, '1')

    self.assertEqual(len(self.requestlog), 0)

  def testCurrentTime(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')

    root = ET.fromstring(h.request.body)
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

    self.assertEqual(len(self.requestlog), 0)

  def testLookupDevIP6(self):
    http.PROC_IF_INET6 = 'testdata/http/if_inet6'
    cpe_machine = self.getCpe()
    self.assertEqual(cpe_machine.LookupDevIP6('eth0'),
                     '11:2233:4455:6677:8899:aabb:ccdd:eeff')
    self.assertEqual(cpe_machine.LookupDevIP6('foo0'), 0)

  def testRetryCount(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')

    root = ET.fromstring(h.request.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '0')

    # Fail the first request
    h.send_error(404)
    self.wait(timeout=20)  # wait for client request to finish and setup retry
    self.advance_time += 10
    h = self.NextHandler()

    root = ET.fromstring(h.request.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '1')

  def testCookies(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertTrue(h.request.method, 'POST')

    msg = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">cwmpID</cwmp:ID><cwmp:HoldRequests soapenv:mustUnderstand="1">1</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:InformResponse><MaxEnvelopes>1</MaxEnvelopes></cwmp:InformResponse></soapenv:Body></soapenv:Envelope>'  # pylint: disable-msg=g-line-too-long

    h.set_cookie('CWMPSID', '0123456789abcdef')
    h.set_cookie('AnotherCookie', '987654321', domain='.example.com',
                 path='/', expires_days=1)
    h.write(msg)
    h.finish()

    h = self.NextHandler()
    self.assertEqual(h.request.headers['Cookie'],
                     'AnotherCookie=987654321; CWMPSID=0123456789abcdef')

  def testRedirect(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    urlbase = 'http://127.0.0.1:%d' % self.get_http_port()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/cwmp')
    h.redirect(urlbase + '/redir7', status=307)
    self.assertTrue('<soap' in h.request.body)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir7')
    h.redirect(urlbase + '/redir1', status=301)
    self.assertTrue('<soap' in h.request.body)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir1')
    h.redirect(urlbase + '/redir2', status=302)
    self.assertTrue('<soap' in h.request.body)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir2')
    self.assertTrue('<soap' in h.request.body)

  def testRedirectSession(self):
    """Test that a redirect persists for the entire session."""
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    urlbase = 'http://127.0.0.1:%d' % self.get_http_port()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/cwmp')
    h.redirect(urlbase + '/redirected', status=307)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redirected')
    h.finish()

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redirected')
    h.finish()

  def testNewPingSession(self):
    cpe_machine = self.getCpe()
    cpe_machine.previous_ping_time = 0

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    ioloop_mock = m.CreateMock(tornado.ioloop.IOLoop)
    m.StubOutWithMock(cpe_machine, '_NewSession')
    StubOutMonotime(m)

    # First call to _NewSession should get the time and trigger a new session
    GetMonotime()().AndReturn(1000)
    cpe_machine._NewSession(mox.IsA(str))

    # Second call to _NewSession should queue a session
    GetMonotime()().AndReturn(1001)
    ioloop_mock.add_timeout(mox.IsA(datetime.timedelta),
                            mox.IgnoreArg()).AndReturn(1)

    # Third call should get the time and then not do anything
    # since a session is queued.
    GetMonotime()().AndReturn(1001)

    # And the call to _NewTimeoutSession should call through to
    # NewPingSession, and start a new session
    GetMonotime()().AndReturn(1000 + cpe_machine.rate_limit_seconds)
    ioloop_mock.add_timeout(mox.IsA(datetime.timedelta),
                            mox.IgnoreArg()).AndReturn(2)
    cpe_machine.ioloop = ioloop_mock
    m.ReplayAll()

    # Real test starts here.
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewTimeoutPingSession()

    # Verify everything was called correctly.
    m.VerifyAll()

  def testNewPeriodicSession(self):
    """Tests that _NewSession is called if the event queue is empty."""
    cpe_machine = self.getCpe()

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    m.StubOutWithMock(cpe_machine, '_NewSession')
    cpe_machine._NewSession('2 PERIODIC')
    m.ReplayAll()

    cpe_machine.NewPeriodicSession()
    m.VerifyAll()

  def testNewPeriodicSessionPending(self):
    """Tests that no new periodic session starts if there is one pending."""
    cpe_machine = self.getCpe()

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    m.StubOutWithMock(cpe_machine, 'Run')
    cpe_machine.Run()
    m.ReplayAll()

    self.assertFalse(('2 PERIODIC', None) in cpe_machine.event_queue)
    cpe_machine.NewPeriodicSession()
    self.assertTrue(('2 PERIODIC', None) in cpe_machine.event_queue)
    cpe_machine.NewPeriodicSession()
    m.ReplayAll()

  def testEventQueue(self):
    cpe_machine = self.getCpe()
    m = mox.Mox()
    m.StubOutWithMock(sys, 'exit')
    sys.exit(1)
    sys.exit(1)
    sys.exit(1)
    sys.exit(1)
    m.ReplayAll()

    for i in range(64):
      cpe_machine.event_queue.append(i)

    cpe_machine.event_queue.append(100)
    cpe_machine.event_queue.appendleft(200)
    cpe_machine.event_queue.extend([300])
    cpe_machine.event_queue.extendleft([400])

    cpe_machine.event_queue.clear()
    cpe_machine.event_queue.append(10)
    cpe_machine.event_queue.clear()
    m.VerifyAll()

  def testEncodeInform(self):
    cpe_machine = self.getCpe()
    cpe_machine.NewPeriodicSession()
    inform = cpe_machine.EncodeInform()
    self.assertTrue(len(inform))
    self.assertTrue('2 PERIODIC' in inform)
    self.assertFalse('4 VALUE CHANGE' in inform)
    cpe_machine.event_queue.append(('4 VALUE CHANGE', None))
    inform = cpe_machine.EncodeInform()
    self.assertTrue(len(inform))
    self.assertTrue('2 PERIODIC' in inform)
    self.assertTrue('4 VALUE CHANGE' in inform)


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
