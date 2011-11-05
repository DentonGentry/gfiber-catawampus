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
import management_server
import tr.core
import tr.tr181_v2_2 as tr181


class DeviceIdBruno(object):
  def __init__(self):
    self.Manufacturer = 'Google'
    self.ManufacturerOUI = '001a11'
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


class DeviceBruno(tr181.Device_v2_2.Device):
  """Device implementation for Bruno, Google's set top box platform.
  """

  def __init__(self):
    tr181.Device_v2_2.Device.__init__(self)
    self.ATM = tr.core.TODO()
    self.Bridging = tr.core.TODO()
    self.CaptivePortal = tr.core.TODO()
    self.DHCPv4 = tr.core.TODO()
    self.DNS = tr.core.TODO()
    self.DSL = tr.core.TODO()
    self.GatewayInfo = tr.core.TODO()
    self.HPNA = tr.core.TODO()
    self.HomePlug = tr.core.TODO()
    self.Hosts = tr.core.TODO()
    self.IEEE8021x = tr.core.TODO()
    self.IP = tr.core.TODO()
    self.LANConfigSecurity = tr.core.TODO()
    self.MoCA = tr.core.TODO()
    self.NAT = tr.core.TODO()
    self.PPP = tr.core.TODO()
    self.PTM = tr.core.TODO()
    self.QoS = tr.core.TODO()
    self.Routing = tr.core.TODO()
    self.Services = tr.core.TODO()
    self.SmartCardReaders = tr.core.TODO()
    self.UPA = tr.core.TODO()
    self.USB = tr.core.TODO()
    self.Users = tr.core.TODO()
    self.WiFi = tr.core.TODO()
    self.InterfaceStackNumberOfEntries = 0

    # Bruno has one Ethernet port, Wifi, and MoCA
    self.Ethernet = ethernet.Ethernet()
    self.Ethernet.AddInterface("eth0", False, ethernet.EthernetInterfaceLinux26)

    self.ManagementServer = management_server.ManagementServer()


def main():
  root = DeviceBruno()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
