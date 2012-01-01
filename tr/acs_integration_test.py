#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Basic integration tests, sending messages from a fake ACS."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import api
import collections
import core
import http
import unittest
import xml.etree.ElementTree as ET


class TestDeviceModelRoot(core.Exporter):
  """A class to hold the device models."""

  def __init__(self):
    core.Exporter.__init__(self)
    params = []
    objects = []
    self.Foo = 'bar'
    params.append('Foo')
    self.Export(params=params, objects=objects)


class MockDownloadManager(object):
  def __init__(self):
    self.new_download_called = False
    self.cancel_called = False
    self.newdl_return = (1, (0.0, 0.0))
    self.cancel_return = (0, '')
    self.queue = list()
    self.queue_num = 1

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
    return self.newdl_return

  def TransferCompleteResponseReceived(self):
    return

  def GetAllQueuedTransfers(self):
    return self.queue

  def AddQueuedTransfer(self):
    q = collections.namedtuple('queued_transfer_struct',
        ('CommandKey State IsDownload FileType FileSize TargetFileName'))
    q.CommandKey = 'CommandKey' + str(self.queue_num)
    self.queue_num += 1
    q.State = 2
    q.IsDownload = True
    q.FileType = "FileType"
    q.FileSize = 123
    q.TargetFileName = "TargetFileName"
    self.queue.append(q)

  def CancelTransfer(self, command_key):
    self.cancel_called = True
    self.cancel_command_key = command_key
    return self.cancel_return


SOAPNS = "{http://schemas.xmlsoap.org/soap/envelope/}"
CWMPNS = "{urn:dslforum-org:cwmp-1-2}"

class TransferRpcTest(unittest.TestCase):
  """Test cases for RPCs relating to file transfers."""
  def getCpe(self):
    root = TestDeviceModelRoot()
    cpe = api.CPE(root)
    cpe.download_manager = MockDownloadManager()
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path="/ping/acs_integration_test",
                              acs=None, acs_url="none://none/",
                              cpe=cpe, cpe_listener=False)
    return cpe_machine

  def testDownloadSimple(self):
    cpe = self.getCpe()
    downloadXml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:Download><CommandKey>CommandKey</CommandKey><FileType>1 Firmware Upgrade Image</FileType><URL>http://example.com/image</URL><Username>Username</Username><Password>Password</Password><FileSize>123456</FileSize><TargetFileName>TargetFileName</TargetFileName><DelaySeconds>321</DelaySeconds><SuccessURL/><FailureURL/></cwmp:Download></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    responseXml = cpe.cpe_soap.Handle(downloadXml)
    self.assertTrue(dm.new_download_called)
    self.assertEqual(dm.newdl_command_key, "CommandKey")
    self.assertEqual(dm.newdl_file_type, "1 Firmware Upgrade Image")
    self.assertEqual(dm.newdl_username, "Username")
    self.assertEqual(dm.newdl_password, "Password")
    self.assertEqual(dm.newdl_file_size, 123456)
    self.assertEqual(dm.newdl_target_filename, "TargetFileName")
    self.assertEqual(dm.newdl_delay_seconds, 321)

    root = ET.fromstring(str(responseXml))
    dlresp = root.find(SOAPNS + 'Body/' + CWMPNS + 'DownloadResponse')
    self.assertTrue(dlresp)
    self.assertEqual(dlresp.find('Status').text, "1")
    self.assertEqual(dlresp.find('StartTime').text, "0001-01-01T00:00:00Z")
    self.assertEqual(dlresp.find('CompleteTime').text, "0001-01-01T00:00:00Z")

  def testDownloadFailed(self):
    cpe = self.getCpe()
    downloadXml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:Download><CommandKey>CommandKey</CommandKey><FileType>1 Firmware Upgrade Image</FileType><URL>invalid</URL><Username>Username</Username><Password>Password</Password><FileSize>123456</FileSize><TargetFileName>TargetFileName</TargetFileName><DelaySeconds>321</DelaySeconds><SuccessURL/><FailureURL/></cwmp:Download></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    dm.newdl_return = (-1, ((9000, 'FaultType'), 'FaultString'))
    responseXml = cpe.cpe_soap.Handle(downloadXml)
    self.assertTrue(dm.new_download_called)
    self.assertEqual(dm.newdl_command_key, "CommandKey")
    self.assertEqual(dm.newdl_file_type, "1 Firmware Upgrade Image")
    self.assertEqual(dm.newdl_username, "Username")
    self.assertEqual(dm.newdl_password, "Password")
    self.assertEqual(dm.newdl_file_size, 123456)
    self.assertEqual(dm.newdl_target_filename, "TargetFileName")
    self.assertEqual(dm.newdl_delay_seconds, 321)

    # We don't do a string compare of the XML output, that is too fragile as a test.
    # We parse the XML and look for expected values. Nonetheless here is what should result:
    expected_response = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>FaultType</faultcode>
            <faultstring>CWMP fault</faultstring>
            <detail>
              <cwmp:Fault>
                <FaultCode>9000</FaultCode>
                <FaultString>FaultString</FaultString>
              </cwmp:Fault>
            </detail>
          </soap:Fault>
        </soap:Body>
      </soap:Envelope>"""

    root = ET.fromstring(str(responseXml))
    dlresp = root.find(SOAPNS + 'Body/' + CWMPNS + 'DownloadResponse')
    self.assertFalse(dlresp)
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, "FaultType")
    self.assertEqual(fault.find('faultstring').text, "CWMP fault")
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, "9000")
    self.assertEqual(detail.find('FaultString').text, "FaultString")

  def testGetAllQueuedTransfers(self):
    cpe = self.getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetAllQueuedTransfers></cwmp:GetAllQueuedTransfers></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    dm.AddQueuedTransfer()
    dm.AddQueuedTransfer()
    responseXml = cpe.cpe_soap.Handle(soapxml)

    # We don't do a string compare of the XML output, that is too fragile as a test.
    # We parse the XML and look for expected values. Nonetheless here is what should result:
    expected = r"""<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
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

    self.assertFalse(dm.new_download_called)
    root = ET.fromstring(str(responseXml))
    transfers = root.findall(SOAPNS + 'Body/' + CWMPNS + 'GetAllQueuedTransfersResponse/TransferList')
    self.assertEqual(len(transfers), 2)
    for i, t in enumerate(transfers):
      self.assertEqual(t.find('CommandKey').text, 'CommandKey' + str(i+1))
      self.assertEqual(t.find('State').text, '2')
      self.assertEqual(t.find('IsDownload').text, 'True')
      self.assertEqual(t.find('FileType').text, 'FileType')
      self.assertEqual(t.find('FileSize').text, '123')
      self.assertEqual(t.find('TargetFileName').text, 'TargetFileName')

  def testGetQueuedTransfers(self):
    cpe = self.getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:GetQueuedTransfers></cwmp:GetQueuedTransfers></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    dm.AddQueuedTransfer()
    dm.AddQueuedTransfer()
    responseXml = cpe.cpe_soap.Handle(soapxml)

    # We don't do a string compare of the XML output, that is too fragile as a test.
    # We parse the XML and look for expected values. Nonetheless here is what should result:
    expected = r"""<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
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

    self.assertFalse(dm.new_download_called)
    root = ET.fromstring(str(responseXml))
    transfers = root.findall(SOAPNS + 'Body/' + CWMPNS + 'GetQueuedTransfersResponse/TransferList')
    self.assertEqual(len(transfers), 2)
    for i, t in enumerate(transfers):
      self.assertEqual(t.find('CommandKey').text, 'CommandKey' + str(i+1))
      self.assertEqual(t.find('State').text, '2')

  def testCancelTransfer(self):
    cpe = self.getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:CancelTransfer><CommandKey>CommandKey</CommandKey></cwmp:CancelTransfer></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    responseXml = cpe.cpe_soap.Handle(soapxml)

    # We don't do a string compare of the XML output, that is too fragile as a test.
    # We parse the XML and look for expected values. Nonetheless here is what should result:
    expected = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <cwmp:CancelTransferResponse />
        </soap:Body>
      </soap:Envelope>"""

    root = ET.fromstring(str(responseXml))
    self.assertTrue(root.findall(SOAPNS + 'Body/' + CWMPNS + 'CancelTransferResponse'))

  def testCancelTransferRefused(self):
    cpe = self.getCpe()
    soapxml = r"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header><cwmp:ID soapenv:mustUnderstand="1">TestCwmpId</cwmp:ID><cwmp:HoldRequests>0</cwmp:HoldRequests></soapenv:Header><soapenv:Body><cwmp:CancelTransfer><CommandKey>CommandKey</CommandKey></cwmp:CancelTransfer></soapenv:Body></soapenv:Envelope>"""
    dm = cpe.cpe.download_manager
    dm.cancel_return = (-1, ((9021, 'FaultType'), 'Refused'))
    responseXml = cpe.cpe_soap.Handle(soapxml)

    # We don't do a string compare of the XML output, that is too fragile as a test.
    # We parse the XML and look for expected values. Nonetheless here is what should result:
    expected = r"""<?xml version="1.0" encoding="utf-8"?>
      <soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
          <cwmp:ID soap:mustUnderstand="1">TestCwmpId</cwmp:ID>
        </soap:Header>
        <soap:Body>
          <soap:Fault>
            <faultcode>FaultType</faultcode>
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

    root = ET.fromstring(str(responseXml))
    fault = root.find(SOAPNS + 'Body/' + SOAPNS + 'Fault')
    self.assertTrue(fault)
    self.assertEqual(fault.find('faultcode').text, "FaultType")
    self.assertEqual(fault.find('faultstring').text, "CWMP fault")
    detail = fault.find('detail/' + CWMPNS + 'Fault')
    self.assertTrue(detail)
    self.assertEqual(detail.find('FaultCode').text, "9021")
    self.assertEqual(detail.find('FaultString').text, "Refused")


if __name__ == '__main__':
  unittest.main()
