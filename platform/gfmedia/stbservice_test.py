#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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
#pylint: disable-msg=C6409

"""Unit tests for stbservice.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import stbservice


class STBServiceTest(unittest.TestCase):
  def setUp(self):
    self.old_PROCNETIGMP = stbservice.PROCNETIGMP
    self.old_PROCNETIGMP6 = stbservice.PROCNETIGMP6
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp'
    stbservice.PROCNETIGMP6 = 'testdata/stbservice/igmp6'

  def tearDown(self):
    stbservice.PROCNETIGMP = self.old_PROCNETIGMP
    stbservice.PROCNETIGMP6 = self.old_PROCNETIGMP6

  def testValidateExports(self):
    stb = stbservice.STBService()
    stb.ValidateExports()

  def testClientGroups(self):
    stb = stbservice.STBService()
    igmp = stb.Components.FrontEndList['1'].IP.IGMP
    self.assertEqual(len(igmp.ClientGroupList), 12)
    expected = set(['224.0.0.1', '225.0.1.3', '225.0.1.6', '225.0.1.10',
                    '225.0.1.13', '225.0.1.18', '225.0.1.20', '225.0.1.153',
                    '225.0.1.158', 'ff02::1', 'ff02::1:ff30:66af',
                    'ff02::1:ff30:64af'])
    actual = set()
    for i in range(1, 13):
      actual.add(igmp.ClientGroupList[i].GroupAddress)
    self.assertEqual(expected, actual)


if __name__ == '__main__':
  unittest.main()
