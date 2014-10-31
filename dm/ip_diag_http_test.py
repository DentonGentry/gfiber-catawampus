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

"""Unit tests for HttpDownloadDiag implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.handle
import tr.mainloop
import ip_diag_http


class HttpDownloadDiagTest(unittest.TestCase):
  """Tests for ip_diag_http.py."""

  def setUp(self):
    super(HttpDownloadDiagTest, self).setUp()
    self.old_CURL = ip_diag_http.CURL
    ip_diag_http.CURL[0] = 'testdata/ip_diag_http/curl'
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    super(HttpDownloadDiagTest, self).tearDown()
    ip_diag_http.CURL = self.old_CURL

  def testValidateExports(self):
    http = ip_diag_http.DiagHttpDownload()
    tr.handle.ValidateExports(http)

  def _WaitUntilCompleted(self, http):
    http.DiagnosticsState = 'Requested'
    while http.DiagnosticsState == 'Requested':
      self.loop.RunOnce(timeout=5)

  def testSimpleFetch(self):
    http = ip_diag_http.DiagHttpDownload()
    http.URL = 'http://www.example.com/'
    self._WaitUntilCompleted(http)
    self.assertEqual(http.DiagnosticsState, 'Complete')
    self.assertTrue('--max-time 60' in http.Result)
    self.assertTrue('--output /dev/null' in http.Result)
    self.assertTrue('--user-agent Catawampus-Http-Diag' in http.Result)
    self.assertTrue('--verbose' in http.Result)
    self.assertTrue('http://www.example.com/' in http.Result)

  def testIPv4Fetch(self):
    http = ip_diag_http.DiagHttpDownload()
    http.URL = 'http://www.example.com/'
    http.IPVersion = 'IPv4'
    self._WaitUntilCompleted(http)
    self.assertEqual(http.DiagnosticsState, 'Complete')
    self.assertTrue('--ipv4' in http.Result)

  def testIPv6Fetch(self):
    http = ip_diag_http.DiagHttpDownload()
    http.URL = 'http://www.example.com/'
    http.IPVersion = 'IPv6'
    self._WaitUntilCompleted(http)
    self.assertEqual(http.DiagnosticsState, 'Complete')
    self.assertTrue('--ipv6' in http.Result)

  def testLimitMbps(self):
    http = ip_diag_http.DiagHttpDownload()
    http.URL = 'http://www.example.com/'
    http.LimitMbps = 30
    self._WaitUntilCompleted(http)
    self.assertEqual(http.DiagnosticsState, 'Complete')
    self.assertTrue('--limit-rate 3750K' in http.Result)

  def testTimeout(self):
    http = ip_diag_http.DiagHttpDownload()
    http.URL = 'http://www.example.com/'
    http.Timeout = 40
    self._WaitUntilCompleted(http)
    self.assertEqual(http.DiagnosticsState, 'Complete')
    self.assertTrue('--max-time 40' in http.Result)


if __name__ == '__main__':
  unittest.main()
