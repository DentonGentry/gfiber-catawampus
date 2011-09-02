#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for tr-181 DeviceInfo implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import unittest
import device_info
import tr.core


class DeviceInfoTest(unittest.TestCase):
  """Tests for device_info.py."""

  def testUptimeSuccess(self):
    ut = device_info.UptimeLinux26()
    ut._proc_uptime = 'testdata/device_info/uptime'
    expected = '123'
    self.assertEqual(ut.GetUptime(), expected)

  def testUptimeFailure(self):
    ut = device_info.UptimeLinux26()
    ut._proc_uptime = 'testdata/device_info/please_do_not_create_this_file'
    expected = '0'
    self.assertEqual(ut.GetUptime(), expected)

  def testMemoryStatusSuccess(self):
    mi = device_info.MemoryStatusLinux26()
    mi._proc_meminfo = 'testdata/device_info/meminfo'
    expected = ('123456', '654321')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryStatusNonexistant(self):
    mi = device_info.MemoryStatusLinux26()
    mi._proc_meminfo = 'testdata/device_info/please_do_not_create_this_file'
    expected = ('0', '0')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryStatusTotal(self):
    mi = device_info.MemoryStatusLinux26()
    mi._proc_meminfo = 'testdata/device_info/meminfo_total'
    expected = ('123456', '0')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testMemoryStatusFree(self):
    mi = device_info.MemoryStatusLinux26()
    mi._proc_meminfo = 'testdata/device_info/meminfo_free'
    expected = ('0', '654321')
    self.assertEqual(mi.GetMemInfo(), expected)

  def testProcessStatusReal(self):
    ps = device_info.ProcessStatusLinux26()
    # This fetches the processes running on the unit test machine. We can't
    # make many assertions about this, just that there should be some processes
    # running.
    processes = ps.ProcessList
    if os.path.exists('/proc/status'):  # otherwise not a Linux machine
      self.assertTrue(processes)

  def testProcessStatusFakeData(self):
    Process = device_info.BASEDEVICE.DeviceInfo.ProcessStatus.Process
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
    ps = device_info.ProcessStatusLinux26()
    ps._slash_proc = 'testdata/device_info/processes'
    processes = ps.ProcessList
    self.assertEqual(len(processes), 6)
    for p in processes.values():
      fake_p = fake_processes[p.PID]
      self.assertEqual(tr.core.Dump(fake_p), tr.core.Dump(p))


class MemoryStatusMock(object):
  def GetMemInfo(self):
    return ('10', '20')


class UptimeMock(object):
  def GetUptime(self):
    return '888'


if __name__ == '__main__':
  unittest.main()
