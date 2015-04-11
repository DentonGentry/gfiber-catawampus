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

"""Unit tests for ManagementServer implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import tr.cpe_management_server
import tr.handle
import management_server


class AcsConfig(object):

  def __init__(self):
    self.CWMPRetryIntervalMultiplier = 1
    self.CWMPRetryMinimumWaitInterval = 2
    self.ConnectionRequestPassword = 'ConnectPassword'
    self.ConnectionRequestUsername = 'ConnectUsername'
    self.ConnectionRequestURL = 'http://example.com/'
    self.DefaultActiveNotificationThrottle = 3
    self.EnableCWMP = True
    self.ParameterKey = 'ParameterKey'
    self.Password = 'Password'
    self.PeriodicInformEnable = False
    self.PeriodicInformInterval = 4
    self.PeriodicInformTime = 5
    self.URL = 'http://example.com/'
    self.Username = 'Username'

  def GetAcsUrl(self):
    return self.URL

  def SetAcsUrl(self, value):
    self.URL = value
    return value


def MakeCpeManagementServer():
  mgmt = tr.cpe_management_server.CpeManagementServer(
      acs_config=AcsConfig(), port=12345, ping_path='')
  mgmt.CWMPRetryIntervalMultiplier = 1
  mgmt.CWMPRetryMinimumWaitInterval = 2
  mgmt.ConnectionRequestPassword = 'ConnectPassword'
  mgmt.ConnectionRequestUsername = 'ConnectUsername'
  mgmt.DefaultActiveNotificationThrottle = 3
  mgmt.Password = 'Password'
  mgmt.PeriodicInformEnable = False
  mgmt.PeriodicInformInterval = 4
  mgmt.PeriodicInformTime = 5
  mgmt.URL = 'http://example.com/'
  mgmt.Username = 'Username'
  return mgmt


class ManagementServerTest(unittest.TestCase):
  """Tests for management_server.py."""

  def testGetMgmt181(self):
    mgmt = MakeCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt181.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt181.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt181.UpgradesManaged)
    self.assertFalse(mgmt181.STUNEnable)
    self.assertEqual(mgmt181.ManageableDeviceNumberOfEntries, 0)
    tr.handle.ValidateExports(mgmt181)

  def testGetMgmt98(self):
    mgmt = MakeCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt98.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt98.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt98.UpgradesManaged)
    self.assertFalse(mgmt98.STUNEnable)
    tr.handle.ValidateExports(mgmt98)

  def testSetMgmt181(self):
    mgmt = MakeCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    self.assertEqual(mgmt181.CWMPRetryIntervalMultiplier, 1)
    mgmt181.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt181.CWMPRetryIntervalMultiplier, 2)
    self.assertRaises(AttributeError, setattr, mgmt181,
                      'ManageableDeviceNumberOfEntries', 1)

  def testSetMgmt98(self):
    mgmt = MakeCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    self.assertEqual(mgmt98.CWMPRetryIntervalMultiplier, 1)
    mgmt98.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt98.CWMPRetryIntervalMultiplier, 2)
    self.assertRaises(AttributeError, setattr, mgmt98,
                      'ManageableDeviceNumberOfEntries', 1)
    self.assertRaises(AttributeError, setattr, mgmt98,
                      'EmbeddedDeviceNumberOfEntries', 2)
    self.assertRaises(AttributeError, setattr, mgmt98,
                      'VirtualDeviceNumberOfEntries', 4)


if __name__ == '__main__':
  unittest.main()
