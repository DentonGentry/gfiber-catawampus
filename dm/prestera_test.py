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

"""Implementation of TR-69 objects for Prestera switch."""

__author__ = 'poist@google.com (Gregory Poist)'

import google3
import prestera
import tr.handle
from tr.wvtest import unittest

prestera.PORTS_JSON_FILE = 'testdata/prestera/ports.json'


class PresteraTest(unittest.TestCase):
  """Tests for prestera.py."""

  def setUp(self):
    pass

  def testValidatePresteraExports(self):
    prestera_obj = prestera.EthernetInterfacePrestera('lan0')
    tr.handle.ValidateExports(prestera_obj)

    self.assertEquals(prestera_obj.Enable, True)
    self.assertEquals(prestera_obj.Status, 'Up')
    self.assertEquals(prestera_obj.LowerLayers, '')
    self.assertEquals(prestera_obj.Name, 'lan0')
    self.assertEquals(prestera_obj.Upstream, False)
    self.assertEquals(prestera_obj.MaxBitRate, 1000)
    self.assertEquals(prestera_obj.DuplexMode, 'Full')
    self.assertEquals(prestera_obj.X_CATAWAMPUS_ORG_ActualBitRate, 1000)
    self.assertEquals(prestera_obj.X_CATAWAMPUS_ORG_ActualDuplexMode, 'Full')

  def testValidatePresteraExportsPort25(self):
    prestera_obj = prestera.EthernetInterfacePrestera('lan25')
    tr.handle.ValidateExports(prestera_obj)

    self.assertEquals(prestera_obj.Enable, True)
    self.assertEquals(prestera_obj.Status, 'Up')
    self.assertEquals(prestera_obj.LowerLayers, '')
    self.assertEquals(prestera_obj.Name, 'lan25')
    self.assertEquals(prestera_obj.Upstream, False)
    self.assertEquals(prestera_obj.MaxBitRate, 10000)
    self.assertEquals(prestera_obj.DuplexMode, 'Full')
    self.assertEquals(prestera_obj.X_CATAWAMPUS_ORG_ActualBitRate, 10000)
    self.assertEquals(prestera_obj.X_CATAWAMPUS_ORG_ActualDuplexMode, 'Full')

  def testValidateEthernetExports(self):
    eth = prestera.EthernetInterfaceStatsPrestera('lan0')
    tr.handle.ValidateExports(eth)

    self.assertEquals(eth.BroadcastPacketsReceived, '300')
    self.assertEquals(eth.BroadcastPacketsSent, '400')
    self.assertEquals(eth.BytesReceived, '1500')
    self.assertEquals(eth.BytesSent, '1400')
    self.assertEquals(eth.DiscardPacketsReceived, '0')
    self.assertEquals(eth.DiscardPacketsSent, '0')
    self.assertEquals(eth.ErrorsReceived, '5400')
    self.assertEquals(eth.ErrorsSent, '1800')
    self.assertEquals(eth.MulticastPacketsReceived, '1900')
    self.assertEquals(eth.MulticastPacketsSent, '2000')
    self.assertEquals(eth.PacketsReceived, '5100')
    self.assertEquals(eth.PacketsSent, '5400')
    self.assertEquals(eth.UnicastPacketsReceived, '2900')
    self.assertEquals(eth.UnicastPacketsSent, '3000')
    self.assertEquals(eth.UnknownProtoPacketsReceived, '0')

  def testValidateEthernetPort24(self):
    eth = prestera.EthernetInterfaceStatsPrestera('lan24')
    tr.handle.ValidateExports(eth)

    self.assertEquals(eth.BroadcastPacketsReceived, '324')
    self.assertEquals(eth.BroadcastPacketsSent, '424')
    self.assertEquals(eth.BytesReceived, '1548')
    self.assertEquals(eth.BytesSent, '1424')
    self.assertEquals(eth.DiscardPacketsReceived, '0')
    self.assertEquals(eth.DiscardPacketsSent, '0')
    self.assertEquals(eth.ErrorsReceived, '5472')
    self.assertEquals(eth.ErrorsSent, '1824')
    self.assertEquals(eth.MulticastPacketsReceived, '1924')
    self.assertEquals(eth.MulticastPacketsSent, '2024')
    self.assertEquals(eth.PacketsReceived, '5172')
    self.assertEquals(eth.PacketsSent, '5472')
    self.assertEquals(eth.UnicastPacketsReceived, '2924')
    self.assertEquals(eth.UnicastPacketsSent, '3024')
    self.assertEquals(eth.UnknownProtoPacketsReceived, '0')

  def testValidateMathOnNonInteger(self):
    eth = prestera.EthernetInterfaceStatsPrestera('lan4')
    tr.handle.ValidateExports(eth)

    self.assertEquals(eth.BytesReceived, '0')
    self.assertEquals(eth.UnicastPacketsReceived, '2904')

  def testJsonReaderWithTestData(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json', 'test')
    self.assertEqual('low', json_reader.GetStat('0/4.testbar', 'mydefault'))

  def testJsonFailToDecode(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json', 'fail')
    self.assertEqual('mydefault', json_reader.GetStat('0/4.foo', 'mydefault'))

  def testDecodeJsonKeyList(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json', 'nest')
    self.assertEqual('deep', json_reader.GetStat('one', 'mydefault'))

  def testDecodeNullJsonKeyList(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json', None)
    self.assertEqual('mydefault', json_reader.GetStat('barre',
                                                      default='mydefault'))

  def testJsonReaderWithMissingJsonFile(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('/this/does/not/exist', 'missingfile')
    self.assertEqual('mydefault', json_reader.GetStat('shouldntmatter',
                                                      default='mydefault'))

  def testNoJsonDataLoaded(self):
    json_reader = prestera.JsonReader()
    self.assertEqual('default', json_reader.GetStat('hi', default='default'))
    self.assertEqual('0', json_reader.GetStat(None))

  def testGetStatWithDottedKey(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual('deep', json_reader.GetStat('nest.one',
                                                 default='mydefault'))

  def testGetStatWithDoubleDottedKey(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual('egg', json_reader.GetStat('nest.next.rotten',
                                                default='mydefault'))

  def testGetStatNoValueNoDefaultStillReturnsSaneDefault(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual('0', json_reader.GetStat(None))

  def testGetStatWithInvalidValue(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual('default', json_reader.GetStat('...', 'default'))

  def testGetStatWithAnotherInvalidValue(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual('default', json_reader.GetStat('test.', 'default'))

  def testGetStatCanReturnDict(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual({'rotten': 'egg'}, json_reader.GetStat('nest.next',
                                                            'default'))

  def testGetStatSupportsBools(self):
    json_reader = prestera.JsonReader()
    json_reader.LoadJsonFromFile('testdata/prestera/test.json')
    self.assertEqual(False, json_reader.GetStat('isFalse', default=True))
    self.assertEqual(True, json_reader.GetStat('isTrue', default=False))


if __name__ == '__main__':
  unittest.main()
