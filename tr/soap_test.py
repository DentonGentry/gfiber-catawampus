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

"""Unit tests for soap.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

from wvtest import unittest

import google3
import soap


xml = """<?xml version="1.0" encoding="UTF-8"?>
  <soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-2"
    xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <soapenv:Header>
      <cwmp:ID soapenv:mustUnderstand="1">acs</cwmp:ID>
      <cwmp:HoldRequests soapenv:mustUnderstand="1">0</cwmp:HoldRequests>
    </soapenv:Header>
    <soapenv:Body>
      <cwmp:Download>
        <CommandKey>MyAwesomeCommandKey</CommandKey>
        <FileType>1 Firmware Upgrade Image</FileType>
        <URL>https://www.example.com/</URL>
        <FileSize>2</FileSize>
        <TargetFileName>MyAwesomeFilename</TargetFileName>
        <DelaySeconds>0</DelaySeconds>
        <SuccessURL/>
        <FailureURL/>
      </cwmp:Download>
    </soapenv:Body>
  </soapenv:Envelope>"""


class SoapTest(unittest.TestCase):
  """Tests for soap."""

  def testNodeWrapper(self):
    req = soap.Parse(xml).Body[0]
    self.assertEqual(req.name, 'Download')
    self.assertEqual(req.URL, 'https://www.example.com/')

  def testNodeWrapperAttributeError(self):
    req = soap.Parse(xml).Body[0]
    self.assertRaises(AttributeError, req.__getattr__, 'Username')
    self.assertEqual(getattr(req, 'DoesNotExist', 'DefaultValue'),
                     'DefaultValue')


if __name__ == '__main__':
  unittest.main()
