#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for ManagementServer implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
sys.path.append("..")
import management_server
import unittest


class MockCpeManagementServer(object):
  def __init__(self):
    self.CWMPRetryIntervalMultiplier = 1
    self.CWMPRetryMinimumWaitInterval = 2
    self.ConnectionRequestPassword = 'ConnectPassword'
    self.ConnectionRequestUsername = 'ConnectUsername'
    self.DefaultActiveNotificationThrottle = 3
    self.EnableCWMP = True
    self.ParameterKey = 'ParameterKey'
    self.Password = 'Password'
    self.PeriodicInformEnable = False
    self.PeriodicInformInterval = 4
    self.PeriodicInformTime = 5
    self.Username = 'Username'

class ManagementServerTest(unittest.TestCase):
  """Tests for management_server.py."""
  def testMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt181.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt181.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt181.UpgradesManaged)

  def testMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt98.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt98.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt98.UpgradesManaged)


if __name__ == '__main__':
  unittest.main()
