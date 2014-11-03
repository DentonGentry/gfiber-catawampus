#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

"""Unit tests for cwmpboolean.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import google3
import cwmplog
from wvtest import unittest


class CwmpLogTest(unittest.TestCase):
  """Tests for boolean formatting."""

  def setUp(self):
    if 'DONT_SHORTEN' in os.environ:
      del os.environ['DONT_SHORTEN']

  def testInform(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(InformXML)
    self.assertEqual(log, InformLog)

  def testInformResponse(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(InformResponseXML)
    self.assertEqual(log, InformResponseLog)

  def testSetParameterValues(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(SetParameterValuesXML)
    self.assertEqual(log, SetParameterValuesLog)

  def testSetParameterValuesResponseSuccess(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(SetParameterValuesResponseSuccessXML)
    self.assertEqual(log, SetParameterValuesResponseSuccessLog)

  def testGetParameterNames(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(GetParameterNamesXML)
    self.assertEqual(log, GetParameterNamesLog)

  def testAddObject(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(AddObjectXML)
    self.assertEqual(log, AddObjectLog)

  def testAddObjectResponse(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(AddObjectResponseXML)
    self.assertEqual(log, AddObjectResponseLog)

  def testCwmpFault(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(CwmpFaultXML)
    self.assertEqual(log, CwmpFaultLog)

  def testGetParameterValues(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(GetParameterValuesXML)
    self.assertEqual(log, GetParameterValuesLog)

  def testGetParameterValuesResponse(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(GetParameterValuesResponseXML)
    self.assertEqual(log, GetParameterValuesResponseLog)

  def testBadXML(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML('this is <not> XML')
    self.assertEqual(log, 'this is <not> XML')

  def testEmpty(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML('')
    self.assertEqual(log, '')

  def testShortening(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(GetParameterValuesResponseLongXML)
    self.assertEqual(log, GetParameterValuesResponseLongLog)

  def testDontShorten(self):
    os.environ['DONT_SHORTEN'] = '1'
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(GetParameterValuesResponseLongXML)
    self.assertEqual(log, GetParameterValuesResponseLongXML)

  def testFullLogs(self):
    logger = cwmplog.Logger(full_logs=2)
    self.assertEqual(logger.LogSoapXML(GetParameterValuesResponseLongXML),
                     GetParameterValuesResponseLongXML)
    self.assertEqual(logger.LogSoapXML(GetParameterValuesResponseLongXML),
                     GetParameterValuesResponseLongXML)
    self.assertEqual(logger.LogSoapXML(GetParameterValuesResponseLongXML),
                     GetParameterValuesResponseLongLog)

  def testKeyPassphrase(self):
    logger = cwmplog.Logger(full_logs=0)
    log = logger.LogSoapXML(KeyPassphraseXML)
    self.assertFalse('password' in log)
    self.assertTrue('ThisIsTheOtherValue' in log)


InformXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">catawampus.1370208445.785391</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:Inform>
      <DeviceId>
        <Manufacturer>Google Fiber</Manufacturer>
        <OUI>F88FCA</OUI>
        <ProductClass>GFHD100</ProductClass>
        <SerialNumber>G00223301811</SerialNumber>
      </DeviceId>
      <Event soap-enc:arrayType="EventStruct[2]">
        <EventStruct>
          <EventCode>0 BOOTSTRAP</EventCode>
          <CommandKey />
        </EventStruct>
        <EventStruct>
          <EventCode>M TRANSFERCOMPLETE</EventCode>
          <CommandKey />
        </EventStruct>
      </Event>
      <MaxEnvelopes>1</MaxEnvelopes>
      <CurrentTime>2013-06-02T21:27:26.080821Z</CurrentTime>
      <RetryCount>0</RetryCount>
      <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[5]">
        <ParameterValueStruct>
          <Name>InternetGatewayDevice.ManagementServer.ConnectionRequestURL</Name>
          <Value xsi:type="xsd:string">http://[2605:a601:fe00:fff7:fa8f:caff:fe00:a28c]:7547/ping/21b19cbcfd821008be9c1938219a1b</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>InternetGatewayDevice.ManagementServer.ParameterKey</Name>
          <Value xsi:type="xsd:string"></Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>InternetGatewayDevice.DeviceInfo.HardwareVersion</Name>
          <Value xsi:type="xsd:string">2</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>InternetGatewayDevice.DeviceInfo.SoftwareVersion</Name>
          <Value xsi:type="xsd:string">gfibertv-32-pre0-14-g8ed95de-dg</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>InternetGatewayDevice.DeviceInfo.SpecVersion</Name>
          <Value xsi:type="xsd:string">1.0</Value>
        </ParameterValueStruct>
      </ParameterList>
    </cwmp:Inform>
  </soap:Body>
</soap:Envelope>"""

InformLog = """ID: catawampus.1370208445.785391
Inform:
  EventCode: 0 BOOTSTRAP
  EventCode: M TRANSFERCOMPLETE
  RetryCount: 0
  InternetGatewayDevice.ManagementServer.ConnectionRequestURL = http://[2605:a601:fe00:fff7:fa8f:caff:fe00:a28c]:7547/ping/21b19cbcfd821008be9c1938219a1b
  InternetGatewayDevice.ManagementServer.ParameterKey = None
  InternetGatewayDevice.DeviceInfo.HardwareVersion = 2
  InternetGatewayDevice.DeviceInfo.SoftwareVersion = gfibertv-32-pre0-14-g8ed95de-dg
  InternetGatewayDevice.DeviceInfo.SpecVersion = 1.0
"""

InformResponseXML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <cwmp:ID soapenv:mustUnderstand="1">catawampus.1370208445.785391</cwmp:ID>
    <cwmp:HoldRequests soapenv:mustUnderstand="1">1</cwmp:HoldRequests>
  </soapenv:Header>
  <soapenv:Body>
    <cwmp:InformResponse>
      <MaxEnvelopes>1</MaxEnvelopes>
    </cwmp:InformResponse>
  </soapenv:Body>
</soapenv:Envelope>"""

InformResponseLog = """ID: catawampus.1370208445.785391
InformResponse:
"""

SetParameterValuesXML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <cwmp:ID soapenv:mustUnderstand="1">google.acs.1370212049608.571675</cwmp:ID>
    <cwmp:HoldRequests soapenv:mustUnderstand="1">1</cwmp:HoldRequests>
  </soapenv:Header>
  <soapenv:Body>
    <cwmp:SetParameterValues>
      <ParameterList soapenc:arrayType="cwmp:ParameterValueStruct[2]">
        <ns5:ParameterValueStruct xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns4="urn:dslforum-org:cwmp-1-0" xmlns:ns5="urn:dslforum-org:cwmp-1-2">
          <Name>InternetGatewayDevice.ManagementServer.PeriodicInformEnable</Name>
          <Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value>
        </ns5:ParameterValueStruct>
        <ns5:ParameterValueStruct xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns4="urn:dslforum-org:cwmp-1-0" xmlns:ns5="urn:dslforum-org:cwmp-1-2">
          <Name>InternetGatewayDevice.ManagementServer.PeriodicInformInterval</Name>
          <Value xsi:type="ns1:unsignedInt">60</Value>
        </ns5:ParameterValueStruct>
      </ParameterList>
      <ParameterKey>GoogleInitConfig</ParameterKey>
    </cwmp:SetParameterValues>
  </soapenv:Body>
</soapenv:Envelope>"""

SetParameterValuesLog = """ID: google.acs.1370212049608.571675
SetParameterValues:
  InternetGatewayDevice.ManagementServer.PeriodicInformEnable = true
  InternetGatewayDevice.ManagementServer.PeriodicInformInterval = 60
"""

SetParameterValuesResponseSuccessXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370212049608.571675</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:SetParameterValuesResponse>
      <Status>0</Status>
    </cwmp:SetParameterValuesResponse>
  </soap:Body>
</soap:Envelope>"""

SetParameterValuesResponseSuccessLog = """ID: google.acs.1370212049608.571675
SetParameterValuesResponse:
  Status: 0
"""

GetParameterNamesXML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <cwmp:ID soapenv:mustUnderstand="1">google.acs.1370215481597.9359765</cwmp:ID>
    <cwmp:HoldRequests soapenv:mustUnderstand="1">0</cwmp:HoldRequests>
  </soapenv:Header>
  <soapenv:Body>
    <cwmp:GetParameterNames>
      <ParameterPath>Device.PeriodicStatistics.SampleSet.</ParameterPath>
      <NextLevel>true</NextLevel>
    </cwmp:GetParameterNames>
  </soapenv:Body>
</soapenv:Envelope>"""

GetParameterNamesLog = """ID: google.acs.1370215481597.9359765
GetParameterNames:
  ParameterPath: Device.PeriodicStatistics.SampleSet.
  NextLevel: true
"""

AddObjectXML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <cwmp:ID soapenv:mustUnderstand="1">google.acs.1370215543274.32355095</cwmp:ID>
    <cwmp:HoldRequests soapenv:mustUnderstand="1">1</cwmp:HoldRequests>
  </soapenv:Header>
  <soapenv:Body>
    <cwmp:AddObject>
      <ObjectName>Device.PeriodicStatistics.SampleSet.1.Parameter.</ObjectName>
      <ParameterKey>GoogleInitConfig</ParameterKey>
    </cwmp:AddObject>
  </soapenv:Body>
</soapenv:Envelope>"""

AddObjectLog = """ID: google.acs.1370215543274.32355095
AddObject:
  ObjectName: Device.PeriodicStatistics.SampleSet.1.Parameter.
"""

AddObjectResponseXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370215543274.32355095</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:AddObjectResponse>
      <InstanceNumber>2</InstanceNumber>
      <Status>0</Status>
    </cwmp:AddObjectResponse>
  </soap:Body>
</soap:Envelope>"""

AddObjectResponseLog = """ID: google.acs.1370215543274.32355095
AddObjectResponse:
  InstanceNumber: 2
  Status: 0
"""

CwmpFaultXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370221731262.21249673</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <soap:Fault>
      <faultcode>Client</faultcode>
      <faultstring>CWMP fault</faultstring>
      <detail>
        <cwmp:Fault>
          <FaultCode>9005</FaultCode>
          <FaultString>No such parameter: Info</FaultString>
        </cwmp:Fault>
      </detail>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""

CwmpFaultLog = """ID: google.acs.1370221731262.21249673
Fault:
  faultcode: Client
  faultstring: CWMP fault
  Fault:
    FaultCode: 9005
    FaultString: No such parameter: Info
"""

GetParameterValuesXML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <cwmp:ID soapenv:mustUnderstand="1">google.acs.1370224916205.16224788</cwmp:ID>
    <cwmp:HoldRequests soapenv:mustUnderstand="1">0</cwmp:HoldRequests>
  </soapenv:Header>
  <soapenv:Body>
    <cwmp:GetParameterValues>
      <ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]">
        <ns5:string xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns4="urn:dslforum-org:cwmp-1-0" xmlns:ns5="urn:dslforum-org:cwmp-1-2">Device.DeviceInfo.UpTime</ns5:string>
      </ParameterNames>
    </cwmp:GetParameterValues>
  </soapenv:Body>
</soapenv:Envelope>"""

GetParameterValuesLog = """ID: google.acs.1370224916205.16224788
GetParameterValues:
  Device.DeviceInfo.UpTime
"""

GetParameterValuesResponseXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370224916205.16224788</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:GetParameterValuesResponse>
      <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[1]">
        <ParameterValueStruct>
          <Name>Device.DeviceInfo.UpTime</Name>
          <Value xsi:type="xsd:unsignedInt">516925</Value>
        </ParameterValueStruct>
      </ParameterList>
    </cwmp:GetParameterValuesResponse>
  </soap:Body>
</soap:Envelope>"""

GetParameterValuesResponseLog = """ID: google.acs.1370224916205.16224788
GetParameterValuesResponse:
  Device.DeviceInfo.UpTime = 516925
"""

GetParameterValuesResponseLongXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370224916205.16224788</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:GetParameterValuesResponse>
      <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[1]">
        <ParameterValueStruct>
          <Name>Device.DeviceInfo.This.Is.A.Very.Long.Parameter.Name.Which.Should.Be.Shortened.In.Order.To.Reduce.The.Footprint.Of.The.Logging</Name>
          <Value xsi:type="xsd:unsignedInt">abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789</Value>
        </ParameterValueStruct>
      </ParameterList>
    </cwmp:GetParameterValuesResponse>
  </soap:Body>
</soap:Envelope>"""

GetParameterValuesResponseLongLog = """ID: google.acs.1370224916205.16224788
GetParameterValuesResponse:
  Device.D.....uce.The.Footprint.Of.The.Logging = abcdefghijklmnop.....ijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789
"""

KeyPassphraseXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <cwmp:ID soap:mustUnderstand="1">google.acs.1370224916205.16224788</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:GetParameterValuesResponse>
      <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[3]">
        <ParameterValueStruct>
          <Name>Foo.1.KeyPassphrase</Name>
          <Value xsi:type="xsd:string">password</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>Foo.1.WEPKey</Name>
          <Value xsi:type="xsd:string">password</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>Foo.1.SomeOtherValue</Name>
          <Value xsi:type="xsd:string">ThisIsTheOtherValue</Value>
        </ParameterValueStruct>
      </ParameterList>
    </cwmp:GetParameterValuesResponse>
  </soap:Body>
</soap:Envelope>"""


if __name__ == '__main__':
  unittest.main()
