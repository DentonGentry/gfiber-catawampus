#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cpe_management_server.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import unittest

import google3
import cpe_management_server as ms
import cwmpdate

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

  def testIsIp6Address(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=5,
                                    ping_path="/ping/path")
    self.assertTrue(cpe_ms.isIp6Address("fe80::21d:9ff:fe11:f55f"))
    self.assertTrue(cpe_ms.isIp6Address("2620:0:1000:5200:222:3ff:fe44:5555"))
    self.assertFalse(cpe_ms.isIp6Address("1.2.3.4"))
    self.assertFalse(cpe_ms.isIp6Address("foobar"))

  def testConnectionRequestURL(self):
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=5,
                                    ping_path="/ping/path")
    cpe_ms.my_ip = "1.2.3.4"
    self.assertEqual(cpe_ms.ConnectionRequestURL, "http://1.2.3.4:5/ping/path")
    cpe_ms.my_ip = "2620:0:1000:5200:222:3ff:fe44:5555"
    self.assertEqual(cpe_ms.ConnectionRequestURL,
                     "http://[2620:0:1000:5200:222:3ff:fe44:5555]:5/ping/path")

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
                                    start_periodic_session=self.start_session,
                                    ioloop = io)
    cpe_ms.SetPeriodicInformEnable("true")
    cpe_ms.SetPeriodicInformTime(cwmpdate.format(datetime.datetime.now()))
    cpe_ms.SetPeriodicInformInterval("1200")

    # Just check that the delay is reasonable
    self.assertNotEqual(io.timeout_time, datetime.timedelta(seconds=0))

  def assertWithinRange(self, c, min, max):
    self.assertTrue(min <= c <= max)

  def testSessionRetryWait(self):
    """Test $SPEC3 Table3 timings."""
    cpe_ms = ms.CpeManagementServer(acs_url_file=None, port=5, ping_path="/")
    for i in range(1000):
      self.assertEqual(cpe_ms.SessionRetryWait(0), 0)
      self.assertTrue(5 <= cpe_ms.SessionRetryWait(1) <= 10)
      self.assertTrue(10 <= cpe_ms.SessionRetryWait(2) <= 20)
      self.assertTrue(20 <= cpe_ms.SessionRetryWait(3) <= 40)
      self.assertTrue(40 <= cpe_ms.SessionRetryWait(4) <= 80)
      self.assertTrue(80 <= cpe_ms.SessionRetryWait(5) <= 160)
      self.assertTrue(160 <= cpe_ms.SessionRetryWait(6) <= 320)
      self.assertTrue(320 <= cpe_ms.SessionRetryWait(7) <= 640)
      self.assertTrue(640 <= cpe_ms.SessionRetryWait(8) <= 1280)
      self.assertTrue(1280 <= cpe_ms.SessionRetryWait(9) <= 2560)
      self.assertTrue(2560 <= cpe_ms.SessionRetryWait(10) <= 5120)
      self.assertTrue(2560 <= cpe_ms.SessionRetryWait(99) <= 5120)
    cpe_ms.CWMPRetryMinimumWaitInterval = 10
    cpe_ms.CWMPRetryIntervalMultiplier = 2500
    for i in range(1000):
      self.assertEqual(cpe_ms.SessionRetryWait(0), 0)
      self.assertTrue(10 <= cpe_ms.SessionRetryWait(1) <= 25)
      self.assertTrue(25 <= cpe_ms.SessionRetryWait(2) <= 62)
      self.assertTrue(62 <= cpe_ms.SessionRetryWait(3) <= 156)
      self.assertTrue(156 <= cpe_ms.SessionRetryWait(4) <= 390)
      self.assertTrue(390 <= cpe_ms.SessionRetryWait(5) <= 976)
      self.assertTrue(976 <= cpe_ms.SessionRetryWait(6) <= 2441)
      self.assertTrue(2441 <= cpe_ms.SessionRetryWait(7) <= 6103)
      self.assertTrue(6103 <= cpe_ms.SessionRetryWait(8) <= 15258)
      self.assertTrue(15258 <= cpe_ms.SessionRetryWait(9) <= 38146)
      self.assertTrue(38146 <= cpe_ms.SessionRetryWait(10) <= 95367)
      self.assertTrue(38146 <= cpe_ms.SessionRetryWait(99) <= 95367)


if __name__ == '__main__':
  unittest.main()
