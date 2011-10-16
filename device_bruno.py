#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import device_info
import ethernet
import tr.core
import tr.tr181_v2_2 as tr181


class DeviceIdBruno(object):
  def __init__(self):
    self.Manufacturer = 'Google'
    self.ManufacturerOUI = '00:1a:11:00:00:00'
    self.ModelName = 'Bruno'
    self.Description = 'Set top box for Google Fiber network'
    self.SerialNumber = '00000000'
    self.HardwareVersion = '0'
    self.AdditionalHardwareVersion = '0'
    self.SoftwareVersion = '0'
    self.AdditionalSoftwareVersion = '0'
    self.ProductClass = 'STB'


class DeviceInfoBruno(device_info.DeviceInfoLinux26):
  def __init__(self):
    device_info.DeviceInfoLinux26.__init__(self, DeviceIdBruno())


class DeviceBruno(tr181.Device_v2_2):
  """Device implementation for Bruno, Google's set top box platform.
  """

  def __init__(self):
    tr181.Device_v2_2.__init__(self)
    self.DeviceInfo = DeviceInfoBruno
    self.SmartCardReaderNumberOfEntries = 0
    self.UserNumberOfEntries = 0

    # Bruno has one Ethernet port, Wifi, and MoCA
    self.Ethernet = ethernet.Ethernet()
    self.Ethernet.add_interface("eth0", False, EthernetInterfaceBrunoEth0)


class EthernetInterfaceBrunoEth0(ethernet.EthernetInterfaceLinux26):
  def __init__(self):
    return EthernetInterfaceLinux26.__init__(self, "eth0")


def main():
  root = DeviceBruno()

if __name__ == '__main__':
  main()
