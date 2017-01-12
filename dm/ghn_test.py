#!/usr/bin/python
# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Unit tests for ghn.py implementation."""

__author__ = 'germuth@google.com (Aaron Germuth)'

import google3
import ghn
from tr.wvtest import unittest


class GhnTest(unittest.TestCase):

  def testGetConfigValue(self):
    ghn.GHN_STATS_FILE = 'testdata/ghn/config'

    self.assertEqual(ghn.GetConfigValue(''), None)
    self.assertEqual(ghn.GetConfigValue('DIDMNG'), None)
    self.assertEqual(ghn.GetConfigValue('NODE'), None)
    self.assertEqual(ghn.GetConfigValue('NO MATCHES'), None)

    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.ENABLE'),
        True)
    self.assertEqual(
        ghn.GetConfigValue('NTP.GENERAL.STATUS'),
        'Unsynchronized')
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DEVICE_ALIAS'),
        'MARVELL GHN NODE')
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DEVICE_NAME'),
        'MARVELL GHN NODE')
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.PRODUCTION.DEVICE_NAME'),
        'DCP962C')
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.LAST_CHANGE'),
        7162)
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.PRODUCTION.MAC_ADDR'),
        'F4:F5:E8:02:C0:2E')
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.API_VERSION'),
        'r521+1+1')
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.FW_VERSION'),
        'dcp962c_v1_x-HN SPIRIT.v7_6_r521+1+1_cvs')
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.FW_VERSION_CORE'),
        'dcp962c_v1_x')
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DOMAIN_NAME'),
        'HomeGrid')
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DNI'),
        5820)
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DOMAIN_ID'),
        13)
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DEVICE_ID'),
        2)
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.NODE_TYPE'),
        'END_POINT')
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.DOMAIN_MASTER_CAPABLE'),
        True)
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.SEC_CONTROLLER_CAPABLE'),
        False)
    self.assertEqual(
        ghn.GetConfigValue('SYSTEM.GENERAL.SEC_CONTROLLER_STATUS'),
        False)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.NUM_DIDS'),
        2)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.DIDS'),
        '0,1,2')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS'),
        'F4:F5:E8:02:C0:29,F4:F5:E8:02:C0:2E')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.TX_BPS'),
        '0,62773,0')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.RX_BPS'),
        '0,62839,0')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.ACTIVE'),
        'NO,YES,YES')

    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DNI', 0),
        5820)
    self.assertEqual(
        ghn.GetConfigValue('NODE.GENERAL.DNI', 1),
        None)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS', -1),
        'F4:F5:E8:02:C0:29,F4:F5:E8:02:C0:2E')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS', 0),
        'F4:F5:E8:02:C0:29')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS', 1),
        'F4:F5:E8:02:C0:2E')
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS', 2),
        None)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.MACS', -2),
        None)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.DIDS', 0),
        0)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.DIDS', 2),
        2)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.DIDS', 3),
        None)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.DIDS', -3),
        None)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.TX_BPS', 1),
        62773)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.ACTIVE', 0),
        False)
    self.assertEqual(
        ghn.GetConfigValue('DIDMNG.GENERAL.ACTIVE', 2),
        True)


if __name__ == '__main__':
  unittest.main()
