#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for http.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import http
import unittest

class CpeManagementServerTest(unittest.TestCase):
  """tests for http.py CpeManagementServer."""
  def testConnectionRequestURL(self):
    cpe_ms = http.CpeManagementServer(None, 5, "/ping/path", None)
    cpe_ms.my_ip = "1.2.3.4"
    self.assertEqual(cpe_ms.ConnectionRequestURL, "http://1.2.3.4:5/ping/path")

  def testUrl(self):
    cpe_ms = http.CpeManagementServer("testdata/http/acs_url_file", 0, "", None)
    self.assertEqual(cpe_ms.URL, 'http://acs.example.com/cwmp')

  def testEmptyUrl(self):
    cpe_ms = http.CpeManagementServer("/no/such/file", 0, "/", None)
    self.assertEqual(cpe_ms.URL, '')

  def GetParameterKey(self):
    return 'ParameterKey'

  def testParameterKey(self):
    cpe_ms = http.CpeManagementServer(None, 0, "/", self.GetParameterKey)
    self.assertEqual(cpe_ms.ParameterKey, self.GetParameterKey())


if __name__ == '__main__':
  unittest.main()
