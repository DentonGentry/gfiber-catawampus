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

"""Unit tests for XML generation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import xml.etree.cElementTree as ET
import xmlwitch
from wvtest import unittest


class XmlWitchTest(unittest.TestCase):
  """Tests for XML generation by xmlwitch."""

  def testInvalidCharacters(self):
    """Test handling of invalid characters in XML."""
    xml = xmlwitch.Builder()
    with xml['test']:
      xml.LessGreater('><')
      xml.ControlCode(chr(0x1a) + chr(0x00))
      xml.BadUnicode(''.join([unichr(0x0080), unichr(0xfffe)]))
      xml.UnicodePaired(''.join([unichr(0xd800), unichr(0xdc00)]))
    s = str(xml)
    self.assertTrue(u'<LessGreater>&gt;&lt;</LessGreater>' in s)
    self.assertFalse(chr(0x1a) in s)
    self.assertFalse(chr(0x00) in s)
    self.assertTrue(u'<ControlCode>??</ControlCode>' in s)
    self.assertFalse(unichr(0x0080) in s)
    self.assertTrue(u'<BadUnicode>??</BadUnicode>' in s)
    self.assertTrue(u'<UnicodePaired>??</UnicodePaired>' in s)
    # just check that it does not raise an exception as ill-formed XML.
    ET.fromstring(s)

  def testALLTheThings111(self):
    """Test all other code points for well-formed XML."""
    xml = xmlwitch.Builder()
    with xml['test']:
      for x in range(0x0, 0xffff):
        xml.Unichr(unichr(x))
      xml.Unimany(''.join([unichr(x) for x in range(0, 0x10000)]))
    # we also incidentally test that fromstring doesn't raise an exception.
    self.assertTrue(ET.fromstring(str(xml)) is not None)


if __name__ == '__main__':
  unittest.main()
