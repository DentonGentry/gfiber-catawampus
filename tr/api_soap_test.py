#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for api_soap.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import api_soap
import datetime
import unittest


expectedTransferComplete = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
  </soap:Header>
  <soap:Body>
    <cwmp:TransferComplete>
      <CommandKey>cmdkey</CommandKey>
      <FaultStruct>
        <FaultCode>123</FaultCode>
        <FaultString>faultstring</FaultString>
      </FaultStruct>
      <StartTime>2011-12-05T12:01:02Z</StartTime>
      <CompleteTime>2011-12-05T12:01:03Z</CompleteTime>
    </cwmp:TransferComplete>
  </soap:Body>
</soap:Envelope>"""


class RpcMessageTest(unittest.TestCase):
  """Tests for formatting of XML objects."""

  def testTransferComplete(self):
    encode = api_soap.Encode()
    start = datetime.datetime(2011, 12, 5, 12, 01, 02);
    end = datetime.datetime(2011, 12, 5, 12, 01, 03);
    xml = str(encode.TransferComplete("cmdkey", 123, "faultstring", start, end))
    self.assertEqual(xml, expectedTransferComplete)


if __name__ == '__main__':
  unittest.main()
