#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cpe_management_server.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
sys.path.append("vendor/tornado")
import cpe_management_server as ms
import cwmpdate
import datetime
import unittest

class MockIoloop(object):
  def __init__(self):
    self.timeout_time = None
    self.timeout_callback = None
    self.remove_timeout = None
    self.handle = 1

  def add_timeout(self, time, callback):
    self.timeout_time = time
    self.timeout_callback = callback
    return self.handle

  def remove_timeout(self, timeout):
    self.remove_timeout = timeout

periodic_callbacks = []
class MockPeriodicCallback(object):
  def __init__(self, callback, callback_time, io_loop=None):
    self.callback = callback
    self.callback_time = callback_time
    self.io_loop = io_loop
    self.start_called = False
    self.stop_called = False
    periodic_callbacks.append(self)

  def start(self):
    self.start_called = True

  def stop(self):
    self.stop_called = True


class CpeManagementServerTest(unittest.TestCase):
  """tests for http.py CpeManagementServer."""
  def setUp(self):
    self.start_session_called = False
    del periodic_callbacks[:]

  def testConnectionRequestURL(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=5,
                                    ping_path="/ping/path")
    cpe_ms.my_ip = "1.2.3.4"
    self.assertEqual(cpe_ms.ConnectionRequestURL, "http://1.2.3.4:5/ping/path")

  def testUrl(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file="testdata/http/acs_url_file",
                                    port=0, ping_path="")
    self.assertEqual(cpe_ms.URL, 'http://acs.example.com/cwmp')

  def testEmptyUrl(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file="/no/such/file", port=0,
                                    ping_path="/")
    self.assertEqual(cpe_ms.URL, '')

  def GetParameterKey(self):
    return 'ParameterKey'

  def testParameterKey(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=0, ping_path="/",
                                    get_parameter_key=self.GetParameterKey)
    self.assertEqual(cpe_ms.ParameterKey, self.GetParameterKey())

  def start_session(self):
    self.start_session_called = True

  def testPeriodicEnable(self):
    ms.PERIODIC_CALLBACK = MockPeriodicCallback
    io = MockIoloop()
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=0, ping_path="/",
                                    start_session=self.start_session,
                                    ioloop = io)
    cpe_ms.SetPeriodicInformEnable("true")
    cpe_ms.SetPeriodicInformInterval("15")
    # cpe_ms should schedule the callbacks when Enable and Interval both set

    self.assertEqual(io.timeout_time, datetime.timedelta(seconds=0))
    self.assertEqual(len(periodic_callbacks), 1)
    cb = periodic_callbacks[0]
    self.assertTrue(cb.callback)
    self.assertEqual(cb.callback_time, 15 * 1000)
    self.assertEqual(cb.io_loop, io)

    io.timeout_callback()
    self.assertTrue(cb.start_called)

  def testPeriodicEnable(self):
    ms.PERIODIC_CALLBACK = MockPeriodicCallback
    io = MockIoloop()
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=0, ping_path="/",
                                    start_session=self.start_session,
                                    ioloop = io)
    cpe_ms.SetPeriodicInformEnable("true")
    cpe_ms.SetPeriodicInformTime(cwmpdate.format(datetime.datetime.now()))
    cpe_ms.SetPeriodicInformInterval("1200")

    # Just check that the delay is reasonable
    self.assertNotEqual(io.timeout_time, datetime.timedelta(seconds=0))



if __name__ == '__main__':
  unittest.main()
