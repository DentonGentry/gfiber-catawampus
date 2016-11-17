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
# pylint:disable=g-bad-import-order
# pylint:disable=line-too-long

"""Unit tests for http.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

# this needs to be first, before any tornado imports
import epoll_fix  # pylint:disable=unused-import

import datetime
import os
import shutil
import sys
import tempfile
import time
from wvtest import unittest
import xml.etree.cElementTree as ET

import google3

import dm_root
import mox
import tornado.httpclient
import tornado.ioloop
import tornado.testing
import tornado.util
import tornado.web

import api
import cpe_management_server
import cwmpdate
import garbage
import handle
import http
import mainloop
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


class FakeAcsConfig(object):

  def __init__(self, port):
    self.port = port
    self.acs_access_attempt_count = 0
    self.success_url = None

  def GetAcsUrl(self):
    return 'http://127.0.0.1:%d/cwmp' % self.port

  def SetAcsUrl(self, val):
    pass

  def AcsAccessAttempt(self, unused_url):
    self.acs_access_attempt_count += 1

  def AcsAccessSuccess(self, url):
    self.success_url = url


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


class _TrivialHandler(tornado.web.RequestHandler):

  def get(self):
    return 'foo'

  def post(self):
    # postdata arrives as bytes, but response can go out as unicode.
    self.write('post-foo: %s' % self.request.body.decode('utf-8'))


class TrivialTest(tornado.testing.AsyncHTTPTestCase, unittest.TestCase):

  def setUp(self):
    super(TrivialTest, self).setUp()
    self.gccheck = garbage.GcChecker()

  def tearDown(self):
    super(TrivialTest, self).tearDown()
    del self._app.handlers
    del self._app
    del self.http_server
    self.gccheck.Done()

  def trivial_callback(self, *args, **kwargs):
    self.trivial_calledback = True

  def get_app(self):
    return tornado.web.Application([('/', _TrivialHandler)])

  def test01(self):
    pass

  def test02(self):
    pass

  def test_query_params(self):
    self.assertEqual(http.AddQueryParams('http://whatever/thing', True),
                     'http://whatever/thing')
    self.assertEqual(http.AddQueryParams('http://whatever/thing', False),
                     'http://whatever/thing?options=noautoprov')
    self.assertEqual(http.AddQueryParams('http://whatever', False),
                     'http://whatever?options=noautoprov')
    self.assertEqual(http.AddQueryParams('//whatever', False),
                     '//whatever?options=noautoprov')
    self.assertEqual(http.AddQueryParams('http://whatever:112', False),
                     'http://whatever:112?options=noautoprov')
    self.assertEqual(http.AddQueryParams('http://whatever:112?x^&y', False),
                     'http://whatever:112?x^&y&options=noautoprov')
    self.assertEqual(http.AddQueryParams('http://what:112?options=x', False),
                     'http://what:112?options=x&options=noautoprov')
    # Doesn't add a new options=noautoprov or reorder options
    self.assertEqual(http.AddQueryParams('//w?x&options=noautoprov&y', False),
                     '//w?x&options=noautoprov&y')
    # Doesn't remove noautoprov even if autoprov=True (we only add options,
    # never remove)
    self.assertEqual(http.AddQueryParams('//w?x&options=noautoprov&y', True),
                     '//w?x&options=noautoprov&y')

  def test_trivial_get(self):
    self.trivial_calledback = False
    self.http_client.fetch(self.get_url('/'), self.stop)
    response = self.wait()
    self.assertIsNone(response.error)
    self.assertFalse(self.trivial_calledback)
    self.assertEqual(response.body, '')
    for fd in self.io_loop._handlers.keys():
      self.io_loop.remove_handler(fd)

  def test_trivial_post(self):
    self.trivial_calledback = False
    # postdata body is provided as unicode, and auto-encoded as utf-8
    self.http_client.fetch(self.get_url('/'), self.stop,
                           method='POST', body=u'hello\u00b4')
    response = self.wait()
    self.assertIsNone(response.error)
    self.assertFalse(self.trivial_calledback)
    for fd in self.io_loop._handlers.keys():
      self.io_loop.remove_handler(fd)
    # post response comes back as utf-8 encoded bytes (not auto-decoded)
    self.assertEqual(bytes(response.body), 'post-foo: hello\xc2\xb4')


class TestManagementServer(object):
  ConnectionRequestUsername = 'username'
  ConnectionRequestPassword = 'password'


class PingTest(tornado.testing.AsyncHTTPTestCase, unittest.TestCase):

  def setUp(self):
    super(PingTest, self).setUp()
    self.gccheck = garbage.GcChecker()

  def tearDown(self):
    super(PingTest, self).tearDown()
    self.gccheck.Done()

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


class HttpTest(tornado.testing.AsyncHTTPTestCase, unittest.TestCase):

  def setUp(self):
    self.gccheck = garbage.GcChecker()
    self.old_HTTPCLIENT = session.HTTPCLIENT
    self.old_GETWANPORT = http.GETWANPORT
    self.want_auto_prov = False
    self.old_WantACSAutoprovisioning = (
        cpe_management_server.CpeManagementServer.WantACSAutoprovisioning)
    cpe_management_server.CpeManagementServer.WantACSAutoprovisioning = (
        lambda(_): self.want_auto_prov)

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
    http.GETWANPORT = self.old_GETWANPORT
    cpe_management_server.CpeManagementServer.WantACSAutoprovisioning = (
        self.old_WantACSAutoprovisioning)

    SetMonotime(self.old_monotime)
    for d in self.removedirs:
      shutil.rmtree(d)
    for f in self.removefiles:
      os.remove(f)
    super(HttpTest, self).tearDown()

    # clean up the namespace to make it easier to see "real" memory leaks
    del self.app.handlers[:]
    del self.app.handlers
    self.app.__dict__.clear()
    del self.app
    del self._app
    del self.http_server

    if self.requestlog:
      raise Exception('requestlog still has %d unhandled requests'
                      % len(self.requestlog))

    self.gccheck.Done()
    self.gccheck = None

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
    # Ensure time marches forward some small amount with each call
    # or the network code in tornado sometimes fails to work.
    self.advance_time += 0.01
    return self.advance_time

  def getCpe(self):
    dm_root.PLATFORMDIR = '../platform'
    root = dm_root.DeviceModelRoot(self.io_loop, 'fakecpe', ext_dir=None)
    cpe = api.CPE(handle.Handle(root))
    dldir = tempfile.mkdtemp()
    self.removedirs.append(dldir)
    cfdir = tempfile.mkdtemp()
    self.removedirs.append(cfdir)
    cpe.download_manager.SetDirectories(config_dir=cfdir, download_dir=dldir)
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path='/ping/http_test',
                              acs=None, cpe=cpe, cpe_listener=False,
                              acs_config=FakeAcsConfig(self.get_http_port()),
                              ioloop=self.io_loop)
    return cpe_machine

  def testA00(self):
    # a trivial test to make sure setUp/tearDown don't leak memory.
    pass

  def testA01(self):
    self.http_client.fetch(self.get_url('/cwmp'), self.stop)
    self.wait()
    h = self.NextHandler()
    self.assertEqual(h.request.method, 'GET')
    h.finish()
    self.wait()

  def testMaxEnvelopes(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')

    root = ET.fromstring(h.request.body)
    h.finish()
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
    h.finish()
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

    self.assertEqual(len(self.requestlog), 0)

  def testLookupDevIP6(self):
    http.PROC_IF_INET6 = 'testdata/http/if_inet6'
    http.GETWANPORT = 'testdata/http/getwanport_eth0'
    cpe_machine = self.getCpe()
    self.assertEqual(cpe_machine.LookupDevIP6(),
                     '11:2233:4455:6677:8899:aabb:ccdd:eeff')
    http.GETWANPORT = 'testdata/http/getwanport_foo0'
    self.assertEqual(cpe_machine.LookupDevIP6(), 0)

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
    # not success, don't bless URL
    self.assertEqual(cpe_machine._acs_config.success_url, None)
    h = self.NextHandler()

    root = ET.fromstring(h.request.body)
    h.finish()
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '1')

  def testCookies(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    self.assertTrue(h.request.method, 'POST')

    msg = ('<soapenv:Envelope '
           'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
           'xmlns:cwmp="urn:dslforum-org:cwmp-1-2" '
           'xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID'
           ' soapenv:mustUnderstand="1">cwmpID</cwmp:ID><cwmp:HoldRequests '
           'soapenv:mustUnderstand="1">1</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:InformResponse><MaxEnvelopes>1</MaxEnvelopes></cwmp:InformResponse></soapenv:Body></soapenv:Envelope>')  # pylint:disable=g-line-too-long

    h.set_cookie('CWMPSID', '0123456789abcdef')
    h.set_cookie('AnotherCookie', '987654321', domain='.example.com',
                 path='/', expires_days=1)
    h.write(msg)
    h.finish()
    self.wait()

    h = self.NextHandler()
    self.assertEqual(h.request.headers['Cookie'],
                     'AnotherCookie=987654321; CWMPSID=0123456789abcdef')
    h.finish()
    self.wait()
    # success, bless the URL
    self.assertEqual(cpe_machine._acs_config.success_url,
                     cpe_machine._acs_config.GetAcsUrl())

  def testRedirect(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    orig_url = cpe_machine._acs_config.GetAcsUrl()

    h = self.NextHandler()
    urlbase = 'http://127.0.0.1:%d' % self.get_http_port()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/cwmp')
    # want_auto_prov defaults to False
    self.assertEqual(h.request.query, 'options=noautoprov')
    h.redirect(urlbase + '/redir7', status=307)
    self.assertTrue('<soap' in h.request.body)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir7')
    # After an HTTP redirect, we don't add our noautoprov option anymore
    # (it's handled at the HTTP layer; the redirector is supposed to keep it
    # if it wants it).
    self.assertEqual(h.request.query, '')
    h.redirect(urlbase + '/redir1', status=301)
    self.assertTrue('<soap' in h.request.body)

    # Session still not complete: success should not be declared yet
    self.assertIsNone(cpe_machine._acs_config.success_url)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir1')
    self.assertEqual(h.request.query, '')
    h.redirect(urlbase + '/redir2', status=302)
    self.assertTrue('<soap' in h.request.body)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir2')
    self.assertEqual(h.request.query, '')
    self.assertTrue('<soap' in h.request.body)
    h.finish()
    self.wait()

    # Session still not complete: success should not be declared yet
    self.assertIsNone(cpe_machine._acs_config.success_url)

    h = self.NextHandler()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/redir2')
    self.assertEqual(h.request.query, '')
    h.finish()
    self.wait()

    # success, bless the *original* URL.
    # (HTTP redirect targets are never blessed)
    self.assertEqual(cpe_machine._acs_config.success_url, orig_url)

  def testRedirectSession(self):
    """Test that a redirect persists for the entire session."""
    SetMonotime(self.advanceTime)
    self.want_auto_prov = True
    cpe_machine = self.getCpe()
    cpe_machine.Startup()

    h = self.NextHandler()
    urlbase = 'http://127.0.0.1:%d' % self.get_http_port()
    self.assertEqual(h.request.method, 'POST')
    self.assertEqual(h.request.path, '/cwmp')
    self.assertEqual(h.request.query, '')
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
    GetMonotime()().AndReturn(1000 + cpe_machine.ping_rate_limit_seconds)
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

  def testNewWakeupSession(self):
    cpe_machine = self.getCpe()

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    m.StubOutWithMock(cpe_machine, 'Run')
    cpe_machine.Run()
    m.ReplayAll()

    self.assertFalse(('6 CONNECTION REQUEST', None) in cpe_machine.event_queue)
    cpe_machine.NewWakeupSession()
    self.assertTrue(('6 CONNECTION REQUEST', None) in cpe_machine.event_queue)
    cpe_machine.NewWakeupSession()
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

  def testAcsDisable(self):
    http.CWMP_TMPDIR = tempfile.mkdtemp()
    self.removedirs.append(http.CWMP_TMPDIR)

    cpe_machine = self.getCpe()
    loop = mainloop.MainLoop()

    http.ACS_DISABLE_EXPIRY_SECS = 60 * 10
    # pylint: disable=protected-access
    acs_disabled_filename = cpe_machine._AcsDisabledFilename()

    # Disable the ACS.  Make sure we logged an access attempt anyway.
    before = cpe_machine._acs_config.acs_access_attempt_count
    open(acs_disabled_filename, 'w')
    loop.RunOnce()
    cpe_machine.NewPeriodicSession()
    cpe_machine.PingReceived()
    self.assertEqual(len(cpe_machine.event_queue), 0)
    after = cpe_machine._acs_config.acs_access_attempt_count
    self.assertNotEqual(before, after)

    # Now test that the file age has expired.  We have to open the file again
    # to trigger _UpdateAcsDisabled.
    http.ACS_DISABLE_EXPIRY_SECS = 0.1
    open(acs_disabled_filename, 'w')
    time.sleep(0.1)
    loop.RunOnce()
    cpe_machine.NewPeriodicSession()
    cpe_machine.PingReceived()
    self.assertEqual(len(cpe_machine.event_queue), 1)

    # Clear the event queue and session, go back a step to the ACS being
    # disabled again, then delete the file and make sure that re-enables it.
    cpe_machine.InformResponseReceived()
    cpe_machine.session = None
    self.assertEqual(len(cpe_machine.event_queue), 0)
    http.ACS_DISABLE_EXPIRY_SECS = 60 * 10
    open(acs_disabled_filename, 'w')
    loop.RunOnce()
    cpe_machine.NewPeriodicSession()
    cpe_machine.PingReceived()
    self.assertEqual(len(cpe_machine.event_queue), 0)
    os.unlink(acs_disabled_filename)
    loop.RunOnce()
    cpe_machine.NewPeriodicSession()
    cpe_machine.PingReceived()
    self.assertEqual(len(cpe_machine.event_queue), 1)

if __name__ == '__main__':
  unittest.main()
