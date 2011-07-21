#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Unit tests for tr-181 DeviceInfo implementation.
"""

__author__ = 'dgentry@google.com (Denny Gentry)'

import device_info
import unittest
import xmlwitch

class DeviceInfoTest(unittest.TestCase):
  def setUp(self):
    pass

  def testUptimeSuccess(self):
    ut = device_info.UptimeLinux26()
    ut._proc_uptime = "testdata/device_info/uptime"
    expected = "123"
    self.assertEqual(ut.GetUptime(), expected)

  def testUptimeFailure(self):
    ut = device_info.UptimeLinux26()
    ut._proc_uptime = "testdata/device_info/please_do_not_create_this_file"
    expected = "0"
    self.assertEqual(ut.GetUptime(), expected)

  def testMemoryInfoSuccess(self):
    mi = device_info.MemoryInfoLinux26()
    mi._proc_meminfo = "testdata/device_info/meminfo"
    expected = ('123456', '654321')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryInfoNonexistant(self):
    mi = device_info.MemoryInfoLinux26()
    mi._proc_meminfo = "testdata/device_info/please_do_not_create_this_file"
    expected = ('0', '0')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryInfoTotal(self):
    mi = device_info.MemoryInfoLinux26()
    mi._proc_meminfo = "testdata/device_info/meminfo_total"
    expected = ('123456', '0')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryInfoFree(self):
    mi = device_info.MemoryInfoLinux26()
    mi._proc_meminfo = "testdata/device_info/meminfo_free"
    expected = ('0', '654321')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testDeviceInfo(self):
    ut = UptimeMock()
    mi = MemoryInfoMock()
    di = device_info.DeviceInfoUno(ut, mi)
    expected = """<DeviceInfo>
  <Manufacturer>Google</Manufacturer>
  <ManufacturerOUI>00:1a:11:00:00:00</ManufacturerOUI>
  <ModelName>Uno</ModelName>
  <Description>CPE device for Google Fiber network</Description>
  <SerialNumber>00000000</SerialNumber>
  <HardwareVersion>0</HardwareVersion>
  <SoftwareVersion>0</SoftwareVersion>
  <UpTime>888</UpTime>
  <MemoryStatus>
    <Total>10</Total>
    <Free>20</Free>
  </MemoryStatus>
</DeviceInfo>"""
    xml = xmlwitch.Builder(encoding='utf-8')
    di.ToXml(xml)
    self.assertEqual(str(xml), expected)


class MemoryInfoMock(object):
  def GetMemInfo(self):
    return ('10', '20')

class UptimeMock(object):
  def GetUptime(self):
    return '888'

if __name__ == '__main__':
  unittest.main()
