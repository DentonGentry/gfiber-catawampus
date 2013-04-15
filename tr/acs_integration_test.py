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
#pylint: disable-msg=C6409

"""Basic integration tests, sending messages from a fake ACS."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import datetime
import unittest
import xml.etree.ElementTree as ET

import google3
import api
import core
import http


SOAPNS = '{http://schemas.xmlsoap.org/soap/envelope/}'
CWMPNS = '{urn:dslforum-org:cwmp-1-2}'
XSINS = '{http://www.w3.org/2001/XMLSchema-instance}'


class TestDeviceModelObject(core.Exporter):
  def __init__(self):
    core.Exporter.__init__(self)
    self.Foo = 'bar'
    self.X_CATAWAMPUS_ORG_Bar = 'baz'
    params = ['Foo', 'X_CATAWAMPUS-ORG_Bar']
    objects = []
    self.Export(params=params, objects=objects)


class TestDeviceModelRootSimple(core.Exporter):
  """A class to hold the device models."""

  def __init__(self):
    core.Exporter.__init__(self)
    params = []
    objects = []
    self.SubObject = TestDeviceModelObject()
    objects.append('SubObject')
    self.Export(params=params, objects=objects)


class TestDeviceModelRoot(core.Exporter):
  """A class to hold the device models."""

  def __init__(self):
    core.Exporter.__init__(self)
    params = []
    objects = []
    self.Foo = 'bar'
    params.append('Foo')
    params.append('RaiseIndexError')
    params.append('RaiseTypeError')
    params.append('RaiseValueError')
    params.append('RaiseSystemError')
    params.append('BooleanParameter')
    params.append('IntegerParameter')
    params.append('FloatParameter')
    params.append('DateTimeParameter')
    params.append('StringParameter')
    params.append('ReadOnlyParameter')
    self.SubObject = TestDeviceModelObject()
    self.ItemList = {}
    self.Item = TestDeviceModelObject
    objects.append('SubObject')
    self.Export(params=params, objects=objects, lists=['Item'])
    self.boolean_parameter = True
    self.boolean_parameter_set = False
    self.start_transaction_called = False
    self.commit_transaction_called = False
    self.abandon_transaction_called = False

    self.IntegerParameter = 100
    self.FloatParameter = 3.14159
    self.DateTimeParameter = datetime.datetime(1999, 12, 31, 23, 59, 58)
    self.StringParameter = 'StringParameter'

  @property
  def RaiseIndexError(self):
    """A parameter which, when accessed, will raise an IndexError."""
    l = list()
    return l[0]

  def GetRaiseTypeError(self):
    """A parameter which, when accessed, will raise a TypeError."""
    raise TypeError('RaiseTypeError Parameter')

  def SetRaiseTypeError(self, value):
    raise TypeError('RaiseTypeError Parameter')

  RaiseTypeError = property(GetRaiseTypeError, SetRaiseTypeError, None,
                            'RaiseTypeError')

  def GetRaiseValueError(self):
    """A parameter which, when accessed, will raise a ValueError."""
    raise ValueError('RaiseValueError Parameter')

  def SetRaiseValueError(self, value):
    raise ValueError('RaiseValueError Parameter')

  RaiseValueError = property(GetRaiseValueError, SetRaiseValueError, None,
                             'RaiseValueError')

  def GetRaiseSystemError(self):
    """A parameter which, when accessed, will raise a SystemError."""
    raise SystemError('RaiseSystemError Parameter')

  def SetRaiseSystemError(self, value):
    raise SystemError('RaiseSystemError Parameter')

  RaiseSystemError = property(GetRaiseSystemError, SetRaiseSystemError, None,
                              'RaiseSystemError')

  def GetBooleanParameter(self):
    return self.boolean_parameter

  def SetBooleanParameter(self, value):
    self.boolean_parameter = value
    self.boolean_parameter_set = True

  BooleanParameter = property(GetBooleanParameter, SetBooleanParameter, None,
                              'BooleanParameter')

  def GetReadOnlyParameter(self):
    return True

  ReadOnlyParameter = property(GetReadOnlyParameter, None, None, 'ReadOnlyParameter')

  def StartTransaction(self):
    self.start_transaction_called = True

  def CommitTransaction(self):
    self.commit_transaction_called = True

  def AbandonTransaction(self):
    self.abandon_transaction_called = True


class MockDownloadManager(object):
  def __init__(self):
    self.new_download_called = False
    self.cancel_called = False
    self.newdl_return = (1, 0.0, 0.0)
    self.newdl_raise_resources = False
    self.newdl_raise_protocol = False
    self.cancel_raise = False
    self.queue = list()
    self.queue_num = 1
    self.reboot_called = False

  def NewDownload(self, command_key=None, file_type=None, url=None,
                  username=None, password=None, file_size=0,
                  target_filename=None, delay_seconds=0):
    self.new_download_called = True
    self.newdl_command_key = command_key
    self.newdl_file_type = file_type
    self.newdl_url = url
    self.newdl_username = username
    self.newdl_password = password
    self.newdl_file_size = file_size
    self.newdl_target_filename = target_filename
    self.newdl_delay_seconds = delay_seconds
    if self.newdl_raise_resources:
      raise core.ResourcesExceededError('FaultString')
    if self.newdl_raise_protocol:
      raise core.FileTransferProtocolError('FaultString')
    return self.newdl_return

  def TransferCompleteResponseReceived(self):
    return

  def GetAllQueuedTransfers(self):
    return self.queue

  def AddQueuedTransfer(self):
    q = collections.namedtuple(
        'queued_transfer_struct',
        ('CommandKey State IsDownload FileType FileSize TargetFileName'))
    q.CommandKey = 'CommandKey' + str(self.queue_num)
    self.queue_num += 1
    q.State = 2
    q.IsDownload = True
    q.FileType = 'FileType'
    q.FileSize = 123
    q.TargetFileName = 'TargetFileName'
    self.queue.append(q)

  def CancelTransfer(self, command_key):
    self.cancel_called = True
    self.cancel_command_key = command_key
    if self.cancel_raise:
      raise core.CancelNotPermitted('Refused')

  def Reboot(self, command_key):
    self.reboot_called = True
    self.reboot_command_key = command_key


class FakePlatformConfig(object):
  def GetAcsUrl(self):
    return None


def getCpe(simpleroot=False):
  root = TestDeviceModelRootSimple() if simpleroot else TestDeviceModelRoot()
  cpe = api.CPE(root)
  cpe.download_manager = MockDownloadManager()
  cpe_machine = http.Listen(ip=None, port=0,
                            ping_path='/ping/acs_integration_test',
                            acs=None, cpe=cpe, cpe_listener=False,
                            platform_config=FakePlatformConfig())
  return cpe_machine


class TransferRpcTest(unittest.TestCase):
  """Test cases for RPCs relating to file transfers."""

  def testDownloadSimple(self):
    cpe = getCpe()
    downloadXml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:Download><CommandKey>CommandKey</CommandKey><FileType>1 Firmware Upgrade Image</FileType><URL>http://example.com/image</URL><Username>Username</Username><Password>Password</Password><FileSize>123456</FileSize><TargetFileName>TargetFileName</TargetFileName><DelaySeconds>321</DelaySeconds><SuccessURL/><FailureURL/></cwmp:Download></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    dm = cpe.cpe.download_manager
    responseXml = cpe.cpe_soap.Handle(downloadXml)
    print responseXml
    self.assertTrue(dm.new_download_called)
    self.assertEqual(dm.newdl_command_key, 'CommandKey')
    self.assertEqual(dm.newdl_file_type, '1 Firmware Upgrade Image')
    self.assertEqual(dm.newdl_username, 'Username')
    self.assertEqual(dm.newdl_password, 'Password')
    self.assertEqual(dm.newdl_file_size, 123456)
    self.assertEqual(dm.newdl_target_filename, 'TargetFileName')
    self.assertEqual(dm.newdl_delay_seconds, 321)

    root = ET.fromstring(str(responseXml))
    dlresp = root.find(SOAPNS + 'Body/' + CWMPNS + 'DownloadResponse')
    self.assertTrue(dlresp)
    self.assertEqual(dlresp.find('Status').text, '1')
    self.assertEqual(dlresp.find('StartTime').text, '0001-01-01T00:00:00Z')
    self.assertEqual(dlresp.find('CompleteTime').text, '0001-01-01T00:00:00Z')

  def testDownloadFailed(self):
    cpe = getCpe()
    downloadXml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:Download><CommandKey>CommandKey</CommandKey><FileType>1 Firmware Upgrade Image</FileType><URL>invalid</URL><Username>Username</Username><Password>Password</Password><FileSize>123456</FileSize><TargetFileName>TargetFileName</TargetFileName><DelaySeconds>321</DelaySeconds><SuccessURL/><FailureURL/></cwmp:Download></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    dm = cpe.cpe.download_manager
    dm.newdl_raise_resources = True
    responseXml = cpe.cpe_soap.Handle(downloadXml)
    print responseXml
    self.assertTrue(dm.new_download_called)
    self.assertEqual(dm.newdl_command_key, 'CommandKey')
    self.assertEqual(dm.newdl_file_type, '1 Firmware Upgrade Image')
    self.assertEqual(dm.newdl_username, 'Username')
    self.assertEqual(dm.newdl_password, 'Password')
    self.assertEqual(dm.newdl_file_size, 123456)
    self.assertEqual(dm.newdl_target_filename, 'TargetFileName')
    self.assertEqual(dm.newdl_delay_seconds, 321)
    root = ET.fromstring(str(responseXml))
    dlresp = root.find(SOAPNS + 'Body/' + CWMPNS + 'DownloadResponse')
    self.assertFalse(dlresp)
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Server')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9004')
    self.assertEqual(detail.find('FaultString').text, 'FaultString')

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>Server</faultcode>
            <faultstring>CWMP fault</faultstring>
            <detail>
              <cwmp:Fault>
                <FaultCode>9004</FaultCode>
                <FaultString>FaultString</FaultString>
              </cwmp:Fault>
            </detail>
          </soap:Fault>
        </soap:Body>
      </soap:Envelope>"""

  def testGetAllQueuedTransfers(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetAllQueuedTransfers></cwmp:GetAllQueuedTransfers></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    dm = cpe.cpe.download_manager
    dm.AddQueuedTransfer()
    dm.AddQueuedTransfer()
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    self.assertFalse(dm.new_download_called)
    root = ET.fromstring(str(responseXml))
    transfers = root.findall(SOAPNS + 'Body/' + CWMPNS +
                             'GetAllQueuedTransfersResponse/TransferList')
    self.assertEqual(len(transfers), 2)
    for i, t in enumerate(transfers):
      self.assertEqual(t.find('CommandKey').text, 'CommandKey' + str(i+1))
      self.assertEqual(t.find('State').text, '2')
      self.assertEqual(t.find('IsDownload').text, 'True')
      self.assertEqual(t.find('FileType').text, 'FileType')
      self.assertEqual(t.find('FileSize').text, '123')
      self.assertEqual(t.find('TargetFileName').text, 'TargetFileName')

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <soap:Header>
        <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
      </soap:Header>
      <soap:Body>
        <cwmp:GetAllQueuedTransfersResponse>
          <TransferList>
            <CommandKey>CommandKey1</CommandKey>
            <State>2</State>
            <IsDownload>True</IsDownload>
            <FileType>FileType</FileType>
            <FileSize>123</FileSize>
            <TargetFileName>TargetFileName</TargetFileName>
          </TransferList>
          <TransferList>
            <CommandKey>CommandKey2</CommandKey>
            <State>2</State>
            <IsDownload>True</IsDownload>
            <FileType>FileType</FileType>
            <FileSize>123</FileSize>
            <TargetFileName>TargetFileName</TargetFileName>
          </TransferList>
        </cwmp:GetAllQueuedTransfersResponse>
      </soap:Body>
    </soap:Envelope>"""

  def testGetQueuedTransfers(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetQueuedTransfers></cwmp:GetQueuedTransfers></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    dm = cpe.cpe.download_manager
    dm.AddQueuedTransfer()
    dm.AddQueuedTransfer()
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    self.assertFalse(dm.new_download_called)
    root = ET.fromstring(str(responseXml))
    transfers = root.findall(SOAPNS + 'Body/' + CWMPNS +
                             'GetQueuedTransfersResponse/TransferList')
    self.assertEqual(len(transfers), 2)
    for i, t in enumerate(transfers):
      self.assertEqual(t.find('CommandKey').text, 'CommandKey' + str(i+1))
      self.assertEqual(t.find('State').text, '2')

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <soap:Header>
        <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
      </soap:Header>
      <soap:Body>
        <cwmp:GetQueuedTransfersResponse>
          <TransferList>
            <CommandKey>CommandKey1</CommandKey>
            <State>2</State>
          </TransferList>
          <TransferList>
            <CommandKey>CommandKey2</CommandKey>
            <State>2</State>
          </TransferList>
        </cwmp:GetQueuedTransfersResponse>
      </soap:Body>
    </soap:Envelope>"""

  def testCancelTransfer(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:CancelTransfer><CommandKey>CommandKey</CommandKey></cwmp:CancelTransfer></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    self.assertTrue(root.findall(SOAPNS + 'Body/' + CWMPNS +
                                 'CancelTransferResponse'))

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <cwmp:CancelTransferResponse />
        </soap:Body>
      </soap:Envelope>"""

  def testCancelTransferRefused(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:CancelTransfer><CommandKey>CommandKey</CommandKey></cwmp:CancelTransfer></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    dm = cpe.cpe.download_manager
    dm.cancel_raise = True
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Client')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9021')
    self.assertEqual(detail.find('FaultString').text, 'Refused')

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>Client</faultcode>
            <faultstring>CWMP fault</faultstring>
            <detail>
              <cwmp:Fault>
                <FaultCode>9021</FaultCode>
                <FaultString>Refused</FaultString>
              </cwmp:Fault>
            </detail>
          </soap:Fault>
        </soap:Body>
      </soap:Envelope>"""

  def testReboot(self):
    cpe = getCpe()
    dm = cpe.cpe.download_manager
    downloadXml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:Reboot><CommandKey>CommandKey</CommandKey></cwmp:Reboot></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(downloadXml)
    print responseXml
    self.assertTrue(dm.reboot_called)
    self.assertEqual(dm.reboot_command_key, 'CommandKey')
    root = ET.fromstring(str(responseXml))
    rbresp = root.find(SOAPNS + 'Body/' + CWMPNS + 'RebootResponse')
    self.assertTrue(rbresp is not None)


class GetParamsRpcTest(unittest.TestCase):
  """Test cases for RPCs relating to Parameters."""

  def testGetParamValue(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">Foo</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    name = root.find(
        SOAPNS + 'Body/' + CWMPNS +
        'GetParameterValuesResponse/ParameterList/ParameterValueStruct/Name')
    self.assertTrue(name is not None)
    self.assertEqual(name.text, 'Foo')

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <cwmp:GetParameterValuesResponse>
            <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[1]">
              <ParameterValueStruct>
                <Name>Foo</Name>
                <Value xsi:type="xsd:string">bar</Value>
              </ParameterValueStruct>
            </ParameterList>
          </cwmp:GetParameterValuesResponse>
        </soap:Body>
      </soap:Envelope>"""

  def testXsiTypes(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">BooleanParameter</ns3:string><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">IntegerParameter</ns3:string><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">FloatParameter</ns3:string><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">DateTimeParameter</ns3:string><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">StringParameter</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    params = root.findall(
        SOAPNS + 'Body/' + CWMPNS +
        'GetParameterValuesResponse/ParameterList/ParameterValueStruct')
    self.assertEqual(len(params), 5)
    self.assertEqual(params[0].find('Value').get(XSINS + 'type'), 'xsd:boolean')
    self.assertEqual(params[1].find('Value').get(XSINS + 'type'), 'xsd:unsignedInt')
    self.assertEqual(params[2].find('Value').get(XSINS + 'type'), 'xsd:double')
    self.assertEqual(params[3].find('Value').get(XSINS + 'type'), 'xsd:dateTime')
    self.assertEqual(params[4].find('Value').get(XSINS + 'type'), 'xsd:string')

  def testGetParamName(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterNames><ParameterPath/><NextLevel>true</NextLevel></cwmp:GetParameterNames></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    names = root.findall(
        SOAPNS + 'Body/' + CWMPNS +
        'GetParameterNamesResponse/ParameterList/ParameterInfoStruct/Name')
    self.assertEqual(len(names), 13)

  def testGetParamNameRecursive(self):
    cpe = getCpe(simpleroot=True)
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterNames><ParameterPath></ParameterPath><NextLevel>false</NextLevel></cwmp:GetParameterNames></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    names = root.findall(
        SOAPNS + 'Body/' + CWMPNS +
        'GetParameterNamesResponse/ParameterList/ParameterInfoStruct/Name')
    self.assertEqual(len(names), 4)
    self.assertEqual(names[0].text, '.')
    self.assertEqual(names[1].text, 'SubObject.')
    self.assertEqual(names[2].text, 'SubObject.Foo')
    self.assertEqual(names[3].text, 'SubObject.X_CATAWAMPUS-ORG_Bar')

  def _AssertCwmpFaultNopeNotHere(self, root):
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Client')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9005')
    self.assertTrue(detail.find('FaultString').text.find('NopeNotHere'))

  def testSetVendorParam(self):
    cpe = getCpe(simpleroot=True)
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:SetParameterValues><ParameterList><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>SubObject.X_CATAWAMPUS-ORG_Bar</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct></ParameterList><ParameterKey>myParamKey</ParameterKey></cwmp:SetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertFalse(fault)

  def testGetBadParamValue(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">NopeNotHere</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'GetParameterValuesResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>Client</faultcode>
            <faultstring>CWMP fault</faultstring>
            <detail>
              <cwmp:Fault>
                <FaultCode>9005</FaultCode>
                <FaultString>No such parameter: NopeNotHere</FaultString>
              </cwmp:Fault>
            </detail>
          </soap:Fault>
        </soap:Body>
      </soap:Envelope>"""

  def testGetBadParamValueFullPath(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">SubObject.NopeNotHere</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml

    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'GetParameterValuesResponse')
    self.assertTrue(name is None)
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Client')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9005')
    self.assertTrue(
        detail.find('FaultString').text.find('SubObject.NopeNotHere'))

  def testGetBadParamName(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterNames><ParameterPath>NopeNotHere</ParameterPath><NextLevel>true</NextLevel></cwmp:GetParameterNames></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'GetParameterNamesResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

    # We don't do a string compare of the XML output, that is too fragile
    # as a test. We parse the XML and look for expected values. Nonetheless
    # here is roughly what responseXml should look like, if you need to debug
    # this test case:
    _ = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>Client</faultcode>
            <faultstring>CWMP fault</faultstring>
            <detail>
              <cwmp:Fault>
                <FaultCode>9005</FaultCode>
                <FaultString>No such parameter: NopeNotHere</FaultString>
              </cwmp:Fault>
            </detail>
          </soap:Fault>
        </soap:Body>
      </soap:Envelope>"""

  def testBadAddObjectName(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:AddObject><ObjectName>NopeNotHere.</ObjectName><ParameterKey>ParameterKey1</ParameterKey></cwmp:AddObject></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'AddObjectResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

  def testBadAddObjectNameNoDot(self):
    """<ObjectName> does not end in a dot, as spec requires."""
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:AddObject><ObjectName>NopeNotHere</ObjectName><ParameterKey>ParameterKey1</ParameterKey></cwmp:AddObject></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'AddObjectResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

  def testBadDelObjectName(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:DeleteObject><ObjectName>NopeNotHere.</ObjectName><ParameterKey>ParameterKey1</ParameterKey></cwmp:DeleteObject></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'DeleteObjectResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

  def testBadDelObjectNameNoDot(self):
    """<ObjectName> does not end in a dot, as spec requires."""
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:DeleteObject><ObjectName>NopeNotHere</ObjectName><ParameterKey>ParameterKey1</ParameterKey></cwmp:DeleteObject></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    name = root.find(SOAPNS + 'Body/' + CWMPNS + 'DeleteObjectResponse')
    self.assertTrue(name is None)
    self._AssertCwmpFaultNopeNotHere(root)

  def testAddObjects(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:AddObjects><ObjectName>Item.</ObjectName><Count>2</Count><ParameterKey>ParameterKey1</ParameterKey></cwmp:AddObjects></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print 'SFASDFSDFA', responseXml
    root = ET.fromstring(str(responseXml))
    resp = root.find(SOAPNS + 'Body/' + CWMPNS + 'AddObjectsResponse')
    self.assertTrue(resp)
    instances = resp.findall('InstanceNumber')
    self.assertTrue(instances)
    self.assertEqual(len(instances), 2)

  def testNoSuchMethod(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:NoSuchMethod><NoSuchArgument/></cwmp:NoSuchMethod></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Server')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9000')
    self.assertTrue(detail.find('FaultString').text.find('NoSuchMethod'))

  def testInvalidArgument(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">RaiseIndexError</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Client')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9003')

  def testSetParameterValues(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:SetParameterValues><ParameterList><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>BooleanParameter</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct></ParameterList><ParameterKey>myParamKey</ParameterKey></cwmp:SetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    resp = root.find(SOAPNS + 'Body/' + CWMPNS + 'SetParameterValuesResponse')
    self.assertTrue(resp)
    status = resp.find('Status')
    self.assertEqual(status.text, '0')
    self.assertTrue(cpe.cpe.root.start_transaction_called)
    self.assertTrue(cpe.cpe.root.commit_transaction_called)
    self.assertFalse(cpe.cpe.root.abandon_transaction_called)

  def _testSetParameterFault(self, soapxml, expect_faults):
    cpe = getCpe()
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    self.assertFalse(root.find(SOAPNS + 'Body/' +
                               CWMPNS + 'SetParameterValuesResponse'))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Client')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9003')
    self.assertEqual(detail.find('FaultString').text, 'Invalid arguments')
    setfaults = detail.findall('SetParameterValuesFault')
    self.assertEqual(len(setfaults), len(expect_faults))
    for f, (name, code) in zip(setfaults, expect_faults):
      self.assertEqual(f.find('ParameterName').text, name)
      self.assertEqual(f.find('FaultCode').text, str(code))
      self.assertTrue(f.find('FaultString').text)
    print 'done'

  def testSetParameterFault(self):
    print
    print 'testSetParameterFault1'
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:SetParameterValues><ParameterList><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>RaiseTypeError</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>RaiseValueError</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>NoSuchParameter</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>ReadOnlyParameter</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct></ParameterList><ParameterKey>myParamKey</ParameterKey></cwmp:SetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    expect = [('RaiseTypeError', 9006),
              ('RaiseValueError', 9007),
              ('NoSuchParameter', 9005),
              ]
    self._testSetParameterFault(soapxml, expect)

    print
    print 'testSetParameterFault2'
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:SetParameterValues><ParameterList><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>RaiseTypeError</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>RaiseValueError</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>ReadOnlyParameter</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">true</Value></ns2:ParameterValueStruct></ParameterList><ParameterKey>myParamKey</ParameterKey></cwmp:SetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    expect = [('RaiseTypeError', 9006),
              ('RaiseValueError', 9007),
              ]
    self._testSetParameterFault(soapxml, expect)

    print
    print 'testSetParameterFault3'
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:SetParameterValues><ParameterList><ns2:ParameterValueStruct xmlns:ns2="urn:dslforum-org:cwmp-1-2"><Name>ReadOnlyParameter</Name><Value xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:type="xs:boolean">false</Value></ns2:ParameterValueStruct></ParameterList><ParameterKey>myParamKey</ParameterKey></cwmp:SetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    expect = [('ReadOnlyParameter', 9008)]
    self._testSetParameterFault(soapxml, expect)

  def testGetRPCMethods(self):
    cpe = getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetRPCMethods></cwmp:GetRPCMethods></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    methods = root.find(SOAPNS + 'Body/' + CWMPNS +
                        'GetRPCMethodsResponse/MethodList')
    self.assertTrue(methods)
    rpcs = methods.findall('string')
    rpcnames = [r.text for r in rpcs]
    # Before adding RPC Names to this list, READ THIS!
    # If this test fails, its because the CPE is responding to a GetRPCMethods
    # call with an RPC which is not defined in the standard. This is ALMOST
    # CERTAINLY because what should be an internal method has been added to
    # http.py:CPE where the first letter is capitalized. That is how we
    # determine which methods to return: everything with a capitalized
    # first letter.
    # Don't just add the name here and think you are done. You need to
    # make the first character of internal methods a lowercase letter
    # or underscore.
    # Don't feel bad. This comment is here because I made the same mistake.
    expected = ['AddObject', 'AddObjects',
                'CancelTransfer', 'ChangeDUState', 'DeleteObject',
                'Download', 'FactoryReset', 'GetAllQueuedTransfers',
                'GetOptions', 'GetParameterAttributes', 'GetParameterNames',
                'GetParameterValues', 'GetQueuedTransfers', 'GetRPCMethods',
                'Reboot', 'ScheduleDownload', 'ScheduleInform',
                'SetParameterAttributes', 'SetParameterValues', 'SetVouchers',
                'Upload']
    self.assertEqual(rpcnames, expected)

  def testSetParameterAttributes(self):
    cpe = getCpe()
    soapxml = r"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<soapenv:Header>
 <cwmp:ID soapenv:mustUnderstand="1">google.acs.1365618768811.6800571</cwmp:ID>
 <cwmp:HoldRequests soapenv:mustUnderstand="1">0</cwmp:HoldRequests>
</soapenv:Header>
<soapenv:Body>
 <cwmp:SetParameterAttributes>
  <ParameterList>
   <ns5:SetParameterAttributesStruct xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns4="urn:dslforum-org:cwmp-1-0" xmlns:ns5="urn:dslforum-org:cwmp-1-2">
    <Name>ReadOnlyParameter</Name>
    <NotificationChange>true</NotificationChange>
    <Notification>4</Notification>
    <AccessListChange>false</AccessListChange>
    <AccessList/>
   </ns5:SetParameterAttributesStruct>
   <ns5:SetParameterAttributesStruct xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns4="urn:dslforum-org:cwmp-1-0" xmlns:ns5="urn:dslforum-org:cwmp-1-2">
    <Name>SubObject.Foo</Name>
    <NotificationChange>true</NotificationChange>
    <Notification>2</Notification>
    <AccessListChange>false</AccessListChange>
    <AccessList/>
   </ns5:SetParameterAttributesStruct>
 </ParameterList>
 </cwmp:SetParameterAttributes>
</soapenv:Body>
</soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    self.assertEqual(4, cpe.cpe.parameter_attrs.GetParameterAttribute('ReadOnlyParameter', 'Notification'))
    self.assertEqual(2, cpe.cpe.parameter_attrs.GetParameterAttribute('SubObject.Foo', 'Notification'))


  def testInternalError(self):
    cpe = getCpe()
    # RaiseSystemError simulates an unexpected problem which should
    # turn into a SOAP:Fault INTERNAL_ERROR
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetParameterValues><ParameterNames soapenc:arrayType="{urn:dslforum-org:cwmp-1-2}string[1]"><ns3:string xmlns="urn:dslforum-org:cwmp-1-2" xmlns:ns1="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns3="urn:dslforum-org:cwmp-1-2">RaiseSystemError</ns3:string></ParameterNames></cwmp:GetParameterValues></soapenv:Body></soapenv:Envelope>"""  #pylint: disable-msg=C6310
    responseXml = cpe.cpe_soap.Handle(soapxml)
    print responseXml
    root = ET.fromstring(str(responseXml))
    self.assertFalse(root.find(SOAPNS + 'Body/' +
                               CWMPNS + 'GetParameterValuesResponse'))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, 'Server')
    self.assertEqual(fault.find('faultstring').text, 'CWMP fault')
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, '9002')
    self.assertTrue(detail.find('FaultString').text)


if __name__ == '__main__':
  unittest.main()
