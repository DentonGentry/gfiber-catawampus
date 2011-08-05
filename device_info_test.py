#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Unit tests for tr-181 DeviceInfo implementation.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

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

  def testProcessStatusReal(self):
    ps = device_info.ProcessStatusLinux26();
    # This fetches the processes running on the unit test machine. We can't
    # make many assertions about this, just that there should be some processes
    # running.
    processes = ps.GetProcesses()
    assert len(processes) > 0

  def testProcessStatusFakeData(self):
    fake_processes = {
        "1"   : device_info.Process(PID="1", Command="init", Size="551",
                                    Priority="20", CPUTime="81970",
                                    State = "Sleeping"),
        "3"   : device_info.Process(PID="3", Command="migration/0", Size="0",
                                    Priority="-100", CPUTime="591510",
                                    State = "Stopped"),
        "5"   : device_info.Process(PID="5", Command="foobar", Size="0",
                                    Priority="-100", CPUTime="591510",
                                    State = "Zombie"),
        "17"  : device_info.Process(PID="17", Command="bar", Size="0",
                                    Priority="-100", CPUTime="591510",
                                    State = "Uninterruptible"),
        "164" : device_info.Process(PID="164", Command="udevd", Size="288",
                                    Priority="16", CPUTime="300",
                                    State = "Running"),
        "770" : device_info.Process(PID="770", Command="automount", Size="6081",
                                    Priority="20", CPUTime="5515790",
                                    State = "Uninterruptible")
        }
    ps = device_info.ProcessStatusLinux26();
    ps._slash_proc = "testdata/device_info/processes"
    processes = ps.GetProcesses()
    self.assertEqual(len(processes), 6)
    for p in processes:
      fake_p = fake_processes[p.PID];
      self.assertEqual(fake_p, p)

  def testDeviceInfo(self):
    dp = device_info.DeviceInfoUno()
    ut = UptimeMock()
    mi = MemoryInfoMock()
    ps = ProcessStatusMock()
    di = device_info.DeviceInfo(dp, ut, mi, ps)
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
  <Process>
    <0>
      <PID>1000</PID>
      <Command>foo</Command>
      <Size>100</Size>
      <Priority>1</Priority>
      <CPUTime>111111</CPUTime>
      <State>Sleeping</State>
    </0>
    <1>
      <PID>2000</PID>
      <Command>bar</Command>
      <Size>200</Size>
      <Priority>2</Priority>
      <CPUTime>222222</CPUTime>
      <State>Running</State>
    </1>
  </Process>
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

class ProcessStatusMock(object):
  def GetProcesses(self):
    processes = list()
    p = device_info.Process("1000", "foo", "100", "1", "111111", "Sleeping")
    processes.append(p)
    p = device_info.Process("2000", "bar", "200", "2", "222222", "Running")
    processes.append(p)
    return processes

if __name__ == '__main__':
  unittest.main()
