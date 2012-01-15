#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for http.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
sys.path.append("vendor/tornado")
sys.path.append("..")
import api
import core
import cwmpdate
import cwmp_session
import dm_root
import download
import http
import os
import shutil
import tempfile
import tornado.httpclient
import tornado.ioloop
import unittest
import xml.etree.ElementTree as ET


mock_http_clients = list()
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


SOAPNS = "{http://schemas.xmlsoap.org/soap/envelope/}"
CWMPNS = "{urn:dslforum-org:cwmp-1-2}"

class HttpTest(unittest.TestCase):
  def setUp(self):
    self.old_HTTPCLIENT = cwmp_session.HTTPCLIENT
    cwmp_session.HTTPCLIENT = MockHttpClient
    self.removedirs = list()
    self.removefiles = list()
    del mock_http_clients[:]

  def tearDown(self):
    cwmp_session.HTTPCLIENT = self.old_HTTPCLIENT
    for d in self.removedirs:
      shutil.rmtree(d)
    for f in self.removefiles:
      os.remove(f)
    del mock_http_clients[:]

  def getCpe(self):
    loop = tornado.ioloop.IOLoop.instance()
    dm_root.PLATFORMDIR = "../platform"
    root = dm_root.DeviceModelRoot(loop, "fakecpe")
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
                              cpe=cpe, cpe_listener=False)
    return cpe_machine

  def testMaxEnvelopes(self):
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]

    root = ET.fromstring(http.fetch_req.body)
    envelope = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/MaxEnvelopes')
    self.assertTrue(envelope is not None)
    self.assertEqual(envelope.text, "1")

  def testCurrentTime(self):
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]

    root = ET.fromstring(http.fetch_req.body)
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

  def testRetryCount(self):
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.assertEqual(len(mock_http_clients), 1)
    http = mock_http_clients[0]

    root = ET.fromstring(http.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, "0")

    # Fail the first request
    httpresp = tornado.httpclient.HTTPResponse(http.fetch_req, 404)
    http.fetch_callback(httpresp)

    cpe_machine.Startup()
    self.assertEqual(len(mock_http_clients), 2)
    http = mock_http_clients[1]

    root = ET.fromstring(http.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, "1")


if __name__ == '__main__':
  unittest.main()
