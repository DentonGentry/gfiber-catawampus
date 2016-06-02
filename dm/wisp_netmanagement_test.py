#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Unit tests for TR-69 Device.X_CATAWAMPUS_ORG.NetManagement."""

__author__ = 'drivkin@google.com (Dennis Rivkin)'

import google3
import os
from tr.wvtest import unittest
import tr.handle
import wisp_netmanagement


class WispNetManagementTest(unittest.TestCase):
  """Tests for wisp_netmanagement.py."""

  def setUp(self):
    self.oldCFG = wisp_netmanagement.CFG_JSON_FILE
    wisp_netmanagement.CFG_JSON_FILE = 'testdata/config-chimera-cfg.json'

  def tearDown(self):
    wisp_netmanagement.CFG_JSON_FILE = self.oldCFG

  def testValidateNetManagementExports(self):
    netmng_obj = wisp_netmanagement.WispNetManagement()
    tr.handle.ValidateExports(netmng_obj)

  def testEmptyConfiguration(self):
    netmng_obj = wisp_netmanagement.WispNetManagement()
    self.assertEqual(netmng_obj.Configuration, '{}')

  def testChangeConfiguration(self):
    netmng_obj = wisp_netmanagement.WispNetManagement()
    jsonString = '{"this-is-json-value": 2}'
    netmng_obj.Configuration = jsonString
    self.assertEqual(netmng_obj.Configuration, jsonString)
    # jsonString must be persistent.
    new_obj = wisp_netmanagement.WispNetManagement()
    self.assertEqual(new_obj.Configuration, jsonString)
    # remove a file that was created.
    os.remove(wisp_netmanagement.CFG_JSON_FILE)


if __name__ == '__main__':
  unittest.main()
