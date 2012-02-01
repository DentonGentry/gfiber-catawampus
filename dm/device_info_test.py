#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for tr-181 DeviceInfo implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3

import sys
import device_info
import os
import unittest
import tr.core


class TestDeviceId(device_info.DeviceIdMeta):
  def Manufacturer(self):
    return 'Manufacturer'
  def ManufacturerOUI(self):
    return '000000'
  def ModelName(self):
    return 'ModelName'
  def Description(self):
    return 'Description'
  def SerialNumber(self):
    return '00000000'
  def HardwareVersion(self):
    return '0'
  def AdditionalHardwareVersion(self):
    return '0'
  def SoftwareVersion(self):
    return '0'
  def AdditionalSoftwareVersion(self):
    return '0'
  def ProductClass(self):
    return 'ProductClass'
  def ModemFirmwareVersion(self):
    return 'ModemFirmwareVersion'


class DeviceInfoTest(unittest.TestCase):
  """Tests for device_info.py."""
  def setUp(self):
    self.old_PROC_MEMINFO = device_info.PROC_MEMINFO
    self.old_PROC_NET_DEV = device_info.PROC_NET_DEV
    self.old_PROC_UPTIME = device_info.PROC_UPTIME
    self.old_SLASH_PROC = device_info.SLASH_PROC

  def tearDown(self):
    device_info.PROC_MEMINFO = self.old_PROC_MEMINFO
    device_info.PROC_NET_DEV = self.old_PROC_NET_DEV
    device_info.PROC_UPTIME = self.old_PROC_UPTIME
    device_info.SLASH_PROC = self.old_SLASH_PROC

  def testValidate181(self):
    di = device_info.DeviceInfo181Linux26(TestDeviceId())
    di.ValidateExports()

  def testValidate98(self):
    di = device_info.DeviceInfo98Linux26(TestDeviceId())
    di.ValidateExports()

  def testUptimeSuccess(self):
    device_info.PROC_UPTIME = 'testdata/device_info/uptime'
    di = device_info.DeviceInfo181Linux26(TestDeviceId())
    self.assertEqual(di.UpTime, '123')

  def testUptimeFailure(self):
    device_info.PROC_UPTIME = '/please_do_not_create_this_file'
    di = device_info.DeviceInfo181Linux26(TestDeviceId())
    self.assertEqual(di.UpTime, '0')

  def testDeviceId(self):
    did = TestDeviceId()
    di = device_info.DeviceInfo181Linux26(did)
    self.assertEqual(did.Manufacturer, di.Manufacturer)
    self.assertEqual(did.ManufacturerOUI, di.ManufacturerOUI)
    self.assertEqual(did.ModelName, di.ModelName)
    self.assertEqual(did.Description, di.Description)
    self.assertEqual(did.SerialNumber, di.SerialNumber)
    self.assertEqual(did.HardwareVersion, di.HardwareVersion)
    self.assertEqual(did.AdditionalHardwareVersion,
                     di.AdditionalHardwareVersion)
    self.assertEqual(did.SoftwareVersion, di.SoftwareVersion)
    self.assertEqual(did.AdditionalSoftwareVersion,
                     di.AdditionalSoftwareVersion)
    self.assertEqual(did.ProductClass, di.ProductClass)

  def testMemoryStatusSuccess(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 123456)
    self.assertEqual(mi.Free, 654321)

  def testMemoryStatusNonexistant(self):
    device_info.PROC_MEMINFO = '/please_do_not_create_this_file'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 0)
    self.assertEqual(mi.Free, 0)

  def testMemoryStatusTotal(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo_total'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 123456)
    self.assertEqual(mi.Free, 0)

  def testMemoryStatusFree(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo_free'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 0)
    self.assertEqual(mi.Free, 654321)

  def testProcessStatusReal(self):
    ps = device_info.ProcessStatusLinux26()
    # This fetches the processes running on the unit test machine. We can't
    # make many assertions about this, just that there should be some processes
    # running.
    processes = ps.ProcessList
    if os.path.exists('/proc/status'):  # otherwise not a Linux machine
      self.assertTrue(processes)

  def testProcessStatusFakeData(self):
    Process = device_info.BASE181DEVICE.DeviceInfo.ProcessStatus.Process
    fake_processes = {
        '1': Process(PID='1', Command='init', Size='551',
                     Priority='20', CPUTime='81970',
                     State='Sleeping'),
        '3': Process(PID='3', Command='migration/0', Size='0',
                     Priority='-100', CPUTime='591510',
                     State='Stopped'),
        '5': Process(PID='5', Command='foobar', Size='0',
                     Priority='-100', CPUTime='591510',
                     State='Zombie'),
        '17': Process(PID='17', Command='bar', Size='0',
                      Priority='-100', CPUTime='591510',
                      State='Uninterruptible'),
        '164': Process(PID='164', Command='udevd', Size='288',
                       Priority='16', CPUTime='300',
                       State='Running'),
        '770': Process(PID='770', Command='automount', Size='6081',
                       Priority='20', CPUTime='5515790',
                       State='Uninterruptible')
        }
    device_info.SLASH_PROC = 'testdata/device_info/processes'
    ps = device_info.ProcessStatusLinux26()
    processes = ps.ProcessList
    self.assertEqual(len(processes), 6)
    for p in processes.values():
      fake_p = fake_processes[p.PID]
      self.assertEqual(tr.core.Dump(fake_p), tr.core.Dump(p))


if __name__ == '__main__':
  unittest.main()
