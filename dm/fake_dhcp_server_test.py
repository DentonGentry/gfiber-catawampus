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

"""Unit tests for fake_dhcp_server implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.handle
import fake_dhcp_server


class FakeDhcpTest(unittest.TestCase):
  """Tests for fake_dhcp_server.py."""

  def setUp(self):
    super(FakeDhcpTest, self).setUp()
    self.dh4 = fake_dhcp_server.Dhcp4Server()
    self.dh4p = fake_dhcp_server.Dhcp4ServerPool()

  def testValidateExports(self):
    dh4 = fake_dhcp_server.Dhcp4Server()
    tr.handle.ValidateExports(dh4)
    dh4p = fake_dhcp_server.Dhcp4ServerPool()
    tr.handle.ValidateExports(dh4p)

  def testStatus(self):
    dh4p = self.dh4p
    self.assertEqual(dh4p.Status, 'Disabled')
    dh4p.Enable = True
    self.assertEqual(dh4p.Status, 'Enabled')


if __name__ == '__main__':
  unittest.main()
