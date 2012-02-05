#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for http.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

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


SOAPNS = "{http://schemas.xmlsoap.org/soap/envelope/}"
CWMPNS = "{urn:dslforum-org:cwmp-1-2}"

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
    dm_root.PLATFORMDIR = "../platform"
    root = dm_root.DeviceModelRoot(self.io_loop, "fakecpe")
    cpe = api.CPE(root)
    dldir = tempfile.mkdtemp()
    self.removedirs.append(dldir)
    download.SetStateDir(dldir)
    acsfile = tempfile.NamedTemporaryFile(delete=False)
    self.removefiles.append(acsfile.name)
    acsfile.write("http://example.com/cwmp")
    acsfile.close()
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path="/ping/acs_integration_test",
                              acs=None, acs_url_file=acsfile.name,
                              cpe=cpe, cpe_listener=False, ioloop=self.io_loop)
    return cpe_machine

  def testMaxEnvelopes(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]
    self.assertTrue(http.fetch_called)

    root = ET.fromstring(http.fetch_req.body)
    envelope = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/MaxEnvelopes')
    self.assertTrue(envelope is not None)
    self.assertEqual(envelope.text, "1")

  def testCurrentTime(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]
    self.assertTrue(http.fetch_called)

    root = ET.fromstring(http.fetch_req.body)
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

  def testRetryCount(self):
    time.time = self.advanceTime
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait(timeout=20)

    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]
    self.assertTrue(http.fetch_called)

    root = ET.fromstring(http.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, "0")

    # Fail the first request
    httpresp = tornado.httpclient.HTTPResponse(http.fetch_req, 404)
    http.fetch_callback(httpresp)

    self.advance_time += 10
    self.wait(timeout=20)
    self.assertEqual(len(mock_http_clients), 2)
    http = mock_http_clients[1]

    root = ET.fromstring(http.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, "1")


if __name__ == '__main__':
  unittest.main()
