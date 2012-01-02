#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Device Models for a simulated CPE."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import device_info
import management_server
import os
import random
import tr.core
import tr.download
import tr.tornadi_fix
import tr.tornado.ioloop
import tr.tr181_v2_2 as tr181


class InstallerFakeCPE(tr.download.Installer):
  def __init__(self, filename, ioloop=None):
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tr.tornado.ioloop.IOLoop.instance()

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
    FAKECPEINSTANCE = os.getenv("FAKECPEINSTANCE", random.randint(1, 99999999))
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

class DeviceInfoFakeCPE(device_info.DeviceInfoLinux26):
  def __init__(self):
    device_info.DeviceInfoLinux26.__init__(self, DeviceIdFakeCPE())


class DeviceFakeCPE(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  def __init__(self):
    tr181.Device_v2_2.Device.__init__(self)
    self.ATM = tr.core.TODO()
    self.Bridging = tr.core.TODO()
    self.CaptivePortal = tr.core.TODO()
    self.DHCPv4 = tr.core.TODO()
    self.DNS = tr.core.TODO()
    self.DSL = tr.core.TODO()
    self.Ethernet = tr.core.TODO()
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
    self.InterfaceStackList = {}

    self.ManagementServer = management_server.ManagementServer()


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerFakeCPE
  tr.download.SetStateDir("/tmp/tr69_dnld.{0}/".format(FakeCPEInstance()))
  params = list()
  objects = list()
  device_model_root.Device = DeviceFakeCPE()
  objects.append('Device')
  device_model_root.DeviceInfo = DeviceInfoFakeCPE()
  objects.append('DeviceInfo')
  return (params, objects)


def main():
  root = DeviceFakeCPE()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
