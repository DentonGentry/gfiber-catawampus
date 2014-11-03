#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Unit tests for tr-181 Device.DNS implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import tempfile
import google3
from tr.wvtest import unittest
import dns
import tr.helpers


class DnsTest(unittest.TestCase):
  """Tests for dns.py."""

  def setUp(self):
    self.old_DNS_CHECK_FILE = dns.DNS_CHECK_FILE[0]
    self.tmpdir = tempfile.mkdtemp()
    (dnsck_handle, self.dnsck_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(dnsck_handle)
    os.unlink(self.dnsck_fname)
    dns.DNS_CHECK_FILE[0] = self.dnsck_fname
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    dns.DNS_CHECK_FILE[0] = self.old_DNS_CHECK_FILE
    tr.helpers.Unlink(self.dnsck_fname)
    os.rmdir(self.tmpdir)

  def testValidateExports(self):
    d = dns.DNS()
    d.ValidateExports()

  def testDnsckFile(self):
    open(self.dnsck_fname, 'w').write('dnsck')
    d = dns.DNS()
    self.assertEqual(d.Diagnostics.X_CATAWAMPUS_ORG_ExtraCheckServers, 'dnsck')
    d.Diagnostics.X_CATAWAMPUS_ORG_ExtraCheckServers = 'dnsck2'
    self.loop.RunOnce()
    self.assertEqual(open(self.dnsck_fname).read(), 'dnsck2\n')


if __name__ == '__main__':
  unittest.main()
