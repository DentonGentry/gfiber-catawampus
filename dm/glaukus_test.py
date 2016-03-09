#!/usr/bin/python
# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Unit tests for TR-69 Device.X_CATAWAMPUS_ORG.Glaukus."""

__author__ = 'cgibson@google.com (Chris Gibson)'

import google3
from tr.wvtest import unittest
import tr.handle
import glaukus

glaukus.MODEM_JSON_FILE = 'testdata/glaukus/modem.json'
glaukus.RADIO_JSON_FILE = 'testdata/glaukus/radio.json'


class GlaukusTest(unittest.TestCase):
  """Tests for glaukus.py."""

  def setUp(self):
    self.json_reader = glaukus.JsonReader()

  def testValidateGlaukusExports(self):
    glaukus_obj = glaukus.Glaukus()
    tr.handle.ValidateExports(glaukus_obj)

  def testValidateModemExports(self):
    modem = glaukus.Modem(self.json_reader)
    tr.handle.ValidateExports(modem)

  def testValidateRadioExports(self):
    radio = glaukus.Radio(self.json_reader)
    tr.handle.ValidateExports(radio)

  def testJsonReaderWithTestData(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json', 'test')
    self.assertEqual('bar', self.json_reader.GetStat('foo', 'mydefault'))

  def testJsonFailToDecode(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json', 'fail')
    self.assertEqual('mydefault', self.json_reader.GetStat('foo', 'mydefault'))

  def testDecodeJsonKeyList(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json',
                                      'test.baz')
    self.assertEqual('hi', self.json_reader.GetStat('barre', 'mydefault'))

  def testDecodeNullJsonKeyList(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json', None)
    self.assertEqual('mydefault', self.json_reader.GetStat('barre',
                                                           default='mydefault'))

  def testJsonReaderWithMissingJsonFile(self):
    self.json_reader.LoadJsonFromFile('/this/does/not/exist', 'missingfile')
    self.assertEqual('mydefault',
                     self.json_reader.GetStat('shouldntmatter',
                                              default='mydefault'))

  def testNoJsonDataLoaded(self):
    self.assertEqual('default',
                     self.json_reader.GetStat('hi', default='default'))
    self.assertEqual(0, self.json_reader.GetStat(None))

  def testGetStatWithDottedKey(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual('bar', self.json_reader.GetStat('test.foo',
                                                     default='mydefault'))

  def testGetStatWithDoubleDottedKey(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual('hi', self.json_reader.GetStat('test.baz.barre',
                                                    default='mydefault'))

  def testGetStatNoValueNoDefaultStillReturnsSaneDefault(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual(0, self.json_reader.GetStat(None))

  def testGetStatWithInvalidValue(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual('default', self.json_reader.GetStat('...', 'default'))

  def testGetStatWithAnotherInvalidValue(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual('default', self.json_reader.GetStat('test.', 'default'))

  def testGetStatCanReturnDict(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/test.json')
    self.assertEqual({'barre': 'hi'}, self.json_reader.GetStat('test.baz',
                                                               'default'))

  def testGetStatSupportsBools(self):
    self.json_reader.LoadJsonFromFile('testdata/glaukus/radio.json')
    self.assertEqual(False, self.json_reader.GetStat('heaterEnabled',
                                                     default=True))
    self.assertEqual(True, self.json_reader.GetStat('paLnaPowerEnabled',
                                                    default=False))


if __name__ == '__main__':
  unittest.main()
