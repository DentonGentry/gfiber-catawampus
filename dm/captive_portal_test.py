#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for captive_portal.py implementation."""

__author__ = 'estrulyov@google.com (Eugene Strulyov)'

import google3
from tr.wvtest import unittest
import tr.session
import captive_portal


# Test version of CaptivePortal that overrides _runCmd() method
class CaptivePortal(captive_portal.CaptivePortal):

  def __init__(self, interfaces):
    super(CaptivePortal, self).__init__()
    self._command = []
    self._interfaces = interfaces

  def _runCmd(self, args):
    self._command = args


class CaptivePortalTest(unittest.TestCase):

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()

  def testOneInterfaceEnable(self):
    cp = CaptivePortal(['wlan0_portal'])
    cp.StartTransaction()
    cp.X_CATAWAMPUS_ORG_Port = 8888
    cp.URL = 'https://youtube.com'
    cp.AllowedList = '1.2.3.4 5.6.7.8'
    cp.Enable = True
    self.loop.RunOnce(timeout=1)

    exp_cmd = [
        captive_portal.CAPTIVE_PORTAL,
        'start',
        '-p',
        '8888',
        '-i',
        'wlan0_portal',
        '-a',
        '1.2.3.4 5.6.7.8'
    ]
    self.assertEquals(exp_cmd, cp._command)
    self.assertEquals(cp.Status, 'Enabled')

  def testTwoInterfaceEnable(self):
    cp = CaptivePortal(['wlan1_portal', 'wlan0_portal'])
    cp.StartTransaction()
    cp.X_CATAWAMPUS_ORG_Port = 8888
    cp.URL = 'https://youtube.com'
    cp.AllowedList = '1.2.3.4 5.6.7.8'
    cp.Enable = True
    self.loop.RunOnce(timeout=1)

    exp_cmd = [
        captive_portal.CAPTIVE_PORTAL,
        'start',
        '-p',
        '8888',
        '-i',
        'wlan1_portal wlan0_portal',
        '-a',
        '1.2.3.4 5.6.7.8'
    ]
    self.assertEquals(exp_cmd, cp._command)
    self.assertEquals(cp.Status, 'Enabled')

  def testDisable(self):
    cp = CaptivePortal(['wlan1_portal', 'wlan0_portal'])
    cp.StartTransaction()
    cp.X_CATAWAMPUS_ORG_Port = 8888
    cp.URL = 'https://youtube.com'
    cp.AllowedList = '1.2.3.4 5.6.7.8'
    cp.Enable = True
    self.loop.RunOnce(timeout=1)

    cp._commands = []
    cp.Enable = False
    self.loop.RunOnce(timeout=1)

    exp_cmd = [
        captive_portal.CAPTIVE_PORTAL,
        'stop',
    ]
    self.assertEquals(exp_cmd, cp._command)
    self.assertEquals(cp.Status, 'Disabled')


if __name__ == '__main__':
  unittest.main()
