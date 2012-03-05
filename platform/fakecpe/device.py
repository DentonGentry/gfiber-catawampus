#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Device Models for a simulated CPE."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import google3
import dm.device_info
import dm.storage
import platform_config
import tornado.ioloop
import tr.core
import tr.download
import tr.tr181_v2_2 as tr181

FAKECPEINSTANCE = None
INTERNAL_ERROR = 9002
BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for FakeCPE."""

  def ConfigDir(self):
    return '/tmp/catawampus.%s/config/' % FakeCPEInstance()

  def DownloadDir(self):
    return '/tmp/catawampus.%s/download/' % FakeCPEInstance()


class InstallerFakeCPE(tr.download.Installer):
  """Fake Installer to install fake images on a fake CPE."""

  def __init__(self, filename, ioloop=None):
    tr.download.Installer.__init__(self)
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
    ftype = file_type.split()
    if ftype and ftype[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(type[0]))
      return False
    self._install_cb = callback

  def reboot(self):
    #TODO(dgentry): Need to exit, and automatically restart
    pass


def FakeCPEInstance():
  global FAKECPEINSTANCE
  if FAKECPEINSTANCE is None:
    FAKECPEINSTANCE = os.getenv('FAKECPEINSTANCE', '99999999')
  return FAKECPEINSTANCE


class DeviceIdFakeCPE(dm.device_info.DeviceIdMeta):
  """Parameters for the DeviceInfo object for a FakeCPE platform."""

  @property
  def Manufacturer(self):
    return 'Catawampus'

  @property
  def ManufacturerOUI(self):
    return '001a11'

  @property
  def ModelName(self):
    return 'FakeCPE'

  @property
  def Description(self):
    return 'Simulated CPE device'

  @property
  def SerialNumber(self):
    return str(FakeCPEInstance())

  @property
  def HardwareVersion(self):
    return '0'

  @property
  def AdditionalHardwareVersion(self):
    return '0'

  @property
  def SoftwareVersion(self):
    return '1'  #TODO(dgentry): need Download to be able to upgrade us

  @property
  def AdditionalSoftwareVersion(self):
    return '0'

  @property
  def ProductClass(self):
    return 'Simulation'

  @property
  def ModemFirmwareVersion(self):
    return '0'


class ServicesFakeCPE(tr181.Device_v2_2.Device.Services):
  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()


class DeviceFakeCPE(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  def __init__(self, device_id):
    super(DeviceFakeCPE, self).__init__()
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='Ethernet')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(objects='IP')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(objects='MoCA')
    self.Unexport(objects='NAT')
    self.Unexport(objects='PPP')
    self.Unexport(objects='PTM')
    self.Unexport(objects='QoS')
    self.Unexport(objects='Routing')
    self.Unexport(objects='SmartCardReaders')
    self.Unexport(objects='UPA')
    self.Unexport(objects='USB')
    self.Unexport(objects='Users')
    self.Unexport(objects='WiFi')

    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.ManagementServer = tr.core.TODO()  # Higher layer code splices this in
    self.Services = ServicesFakeCPE()

    self.InterfaceStackNumberOfEntries = 0
    self.InterfaceStackList = {}


class InternetGatewayDeviceFakeCPE(BASE98IGD):
  def __init__(self, device_id):
    BASE98IGD.__init__(self)
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(lists='LANDevice')
    self.Unexport(objects='LANInterfaces')
    self.Unexport(objects='Layer2Bridging')
    self.Unexport(objects='Layer3Forwarding')
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.Unexport(objects='QueueManagement')
    self.Unexport(objects='Services')
    self.Unexport(objects='Time')
    self.Unexport(objects='TraceRouteDiagnostics')
    self.Unexport(objects='UploadDiagnostics')
    self.Unexport(objects='UserInterface')
    self.Unexport(lists='WANDevice')

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)

  @property
  def LANDeviceNumberOfEntries(self):
    return 0

  @property
  def WANDeviceNumberOfEntries(self):
    return 0


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerFakeCPE
  params = list()
  objects = list()
  devid = DeviceIdFakeCPE()
  device_model_root.Device = DeviceFakeCPE(devid)
  objects.append('Device')
  device_model_root.InternetGatewayDevice = InternetGatewayDeviceFakeCPE(devid)
  objects.append('InternetGatewayDevice')
  return (params, objects)


def main():
  devid = DeviceIdFakeCPE()
  device = DeviceFakeCPE(devid)
  igd = InternetGatewayDeviceFakeCPE(devid)
  tr.core.Dump(device)
  tr.core.Dump(igd)
  device.ValidateExports()
  igd.ValidateExports()
  print 'done'

if __name__ == '__main__':
  main()
