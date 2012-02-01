#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for ManagementServer implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3

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
  def testGetMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt181.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt181.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt181.UpgradesManaged)

  def testGetMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt98.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt98.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt98.UpgradesManaged)

  def testSetMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    mgmt181.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt181.CWMPRetryIntervalMultiplier, 2)

  def testSetMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    mgmt98.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt98.CWMPRetryIntervalMultiplier, 2)

  def testDelMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    delattr(mgmt181, 'CWMPRetryIntervalMultiplier')
    self.assertFalse(hasattr(mgmt, 'CWMPRetryIntervalMultiplier'))

  def testDelMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    delattr(mgmt98, 'CWMPRetryIntervalMultiplier')
    self.assertFalse(hasattr(mgmt, 'CWMPRetryIntervalMultiplier'))


if __name__ == '__main__':
  unittest.main()
