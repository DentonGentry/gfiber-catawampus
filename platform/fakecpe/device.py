#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Device Models for a simulated CPE."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import dm.device_info
import os
import random
import tornado.ioloop
import tr.core
import tr.download
import tr.tr181_v2_2 as tr181


class InstallerFakeCPE(tr.download.Installer):
  def __init__(self, filename, ioloop=None):
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
    type = file_type.split()
    if len(type) > 0 and type[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          "Unsupported file_type {0}".format(type[0]))
      return False
    self._install_cb = callback

  def reboot(self):
    # TODO Need to exit, and automatically restart
    pass


FAKECPEINSTANCE = None
def FakeCPEInstance():
  global FAKECPEINSTANCE
  if FAKECPEINSTANCE is None:
    FAKECPEINSTANCE = os.getenv("FAKECPEINSTANCE", "99999999")
  return FAKECPEINSTANCE


class DeviceIdFakeCPE(object):
  def __init__(self):
    self.Manufacturer = 'Catawampus'
    self.ManufacturerOUI = '012345'
    self.ModelName = "FakeCPE"
    self.Description = "Simulated CPE device"
    self.SerialNumber = str(FakeCPEInstance())
    self.HardwareVersion = '0'
    self.AdditionalHardwareVersion = '0'
    self.SoftwareVersion = '1'  # TODO need Download to be able to upgrade us
    self.AdditionalSoftwareVersion = '0'
    self.ProductClass = 'Simulation'

class DeviceInfoFakeCPE(dm.device_info.DeviceInfoLinux26):
  def __init__(self):
    dm.device_info.DeviceInfoLinux26.__init__(self, DeviceIdFakeCPE())


class DeviceFakeCPE(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  def __init__(self):
    tr181.Device_v2_2.Device.__init__(self)
    self.Unexport(objects="ATM")
    self.Unexport(objects="Bridging")
    self.Unexport(objects="CaptivePortal")
    self.Unexport(objects="DHCPv4")
    self.Unexport(objects="DNS")
    self.Unexport(objects="DSL")
    self.Unexport(objects="Ethernet")
    self.Unexport(objects="GatewayInfo")
    self.Unexport(objects="HPNA")
    self.Unexport(objects="HomePlug")
    self.Unexport(objects="Hosts")
    self.Unexport(objects="IEEE8021x")
    self.Unexport(objects="IP")
    self.Unexport(objects="LANConfigSecurity")
    self.Unexport(objects="MoCA")
    self.Unexport(objects="NAT")
    self.Unexport(objects="PPP")
    self.Unexport(objects="PTM")
    self.Unexport(objects="QoS")
    self.Unexport(objects="Routing")
    self.Unexport(objects="Services")
    self.Unexport(objects="SmartCardReaders")
    self.Unexport(objects="UPA")
    self.Unexport(objects="USB")
    self.Unexport(objects="Users")
    self.Unexport(objects="WiFi")

    self.DeviceInfo = DeviceInfoFakeCPE()
    self.ManagementServer = tr.core.TODO()  # Higher layer code splices this in

    self.InterfaceStackNumberOfEntries = 0
    self.InterfaceStackList = {}


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerFakeCPE
  tr.download.SetStateDir("/tmp/tr69_dnld.{0}/".format(FakeCPEInstance()))
  params = list()
  objects = list()
  device_model_root.Device = DeviceFakeCPE()
  objects.append('Device')
  return (params, objects)


def main():
  root = DeviceFakeCPE()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
