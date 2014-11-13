#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name
# pylint:disable=unused-argument

"""Device Models for a simulated CPE."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import sys
import google3
import dm.device_info
import dm.fake_dhcp_server
import dm.fakemoca
import dm.fakewifi
import dm.igd_time
import dm.periodic_statistics
import dm.storage
import platform_config
import tornado.ioloop
import tr.acs_config
import tr.core
import tr.cwmptypes
import tr.download
import tr.tr098_v1_4
import tr.tr181_v2_2 as tr181


FAKECPEINSTANCE = None
INTERNAL_ERROR = 9002
BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for FakeCPE."""

  def __init__(self, ioloop=None):
    super(PlatformConfig, self).__init__()
    tr.acs_config.SET_ACS = 'true'

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

  def install(self, file_type, unused_target_filename, callback):
    ftype = file_type.split()
    if ftype and ftype[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(type[0]))
      return False
    self._install_cb = callback
    os.rename(self.filename, 'download.tgz')
    self._call_callback(0, '')
    return True

  def reboot(self):
    sys.exit(32)


def FakeCPEInstance():
  global FAKECPEINSTANCE
  if FAKECPEINSTANCE is None:
    FAKECPEINSTANCE = os.getenv('FAKECPEINSTANCE', '99999999')
  return FAKECPEINSTANCE


class DeviceIdFakeCPE(dm.device_info.DeviceIdMeta):
  """Parameters for the DeviceInfo object for a FakeCPE platform."""
  AdditionalHardwareVersion = tr.cwmptypes.ReadOnlyString('0')
  AdditionalSoftwareVersion = tr.cwmptypes.ReadOnlyString('0')
  Description = tr.cwmptypes.ReadOnlyString('Simulated CPE device')
  HardwareVersion = tr.cwmptypes.ReadOnlyString('0')
  Manufacturer = tr.cwmptypes.ReadOnlyString('Catawampus')
  ManufacturerOUI = tr.cwmptypes.ReadOnlyString('001A11')
  ModelName = tr.cwmptypes.ReadOnlyString('FakeCPE')
  ModemFirmwareVersion = tr.cwmptypes.ReadOnlyString('0')
  ProductClass = tr.cwmptypes.ReadOnlyString('Simulation')
  SerialNumber = tr.cwmptypes.ReadOnlyString(FakeCPEInstance())

  @property
  def SoftwareVersion(self):
    try:
      with open('platform/fakecpe/version', 'r') as f:
        return f.readline().strip()
    except IOError:
      return 'unknown_version'


class ServicesFakeCPE(tr181.Device_v2_2.Device.Services):

  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()


class DeviceFakeCPE(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  InterfaceStackNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceStackList')

  def __init__(self, device_id, periodic_stats=None):
    super(DeviceFakeCPE, self).__init__()
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects=['ATM', 'Bridging', 'CaptivePortal',
                           'DHCPv6', 'DNS', 'DSL', 'DSLite', 'Firewall',
                           'GatewayInfo', 'HPNA', 'HomePlug', 'Hosts',
                           'IEEE8021x', 'IPv6rd', 'LANConfigSecurity', 'NAT',
                           'NeighborDiscovery', 'PPP', 'PTM', 'QoS',
                           'RouterAdvertisement', 'Routing', 'SmartCardReaders',
                           'UPA', 'USB', 'Users', 'WiFi'])

    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.DHCPv4 = dm.fake_dhcp_server.DHCPv4()
    self.ManagementServer = tr.core.TODO()  # Higher layer code splices this in
    self.Services = ServicesFakeCPE()

    self.InterfaceStackList = {}

    if periodic_stats:
      self.Export(objects=['PeriodicStatistics'])
      self.PeriodicStatistics = periodic_stats

    self.Ethernet = EthernetFakeCPE()
    self.IP = IPFakeCPE()
    self.MoCA = dm.fakemoca.FakeMoca()


class EthernetFakeCPE(tr181.Device_v2_2.Device.Ethernet):
  """Implements Device_v2_2.Device.Ethernet for FakeCPE platform."""

  InterfaceNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceList')
  LinkNumberOfEntries = tr.cwmptypes.NumberOf('LinkList')
  VLANTerminationNumberOfEntries = tr.cwmptypes.NumberOf('VLANTerminationList')

  def __init__(self):
    super(EthernetFakeCPE, self).__init__()
    self.InterfaceList = {}
    self.LinkList = {}
    self.VLANTerminationList = {}


class IPFakeCPE(tr181.Device_v2_2.Device.IP):
  """Implements Device_v2_2.Device.IP for FakeCPE Platform."""
  # Enable fields are supposed to be writeable; we don't support that.
  IPv4Capable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4Status = tr.cwmptypes.ReadOnlyString('Enabled')
  IPv6Capable = tr.cwmptypes.ReadOnlyBool(True)
  IPv6Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv6Status = tr.cwmptypes.ReadOnlyString('Enabled')

  InterfaceNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceList')
  ActivePortNumberOfEntries = tr.cwmptypes.NumberOf('ActivePortList')

  def __init__(self):
    super(IPFakeCPE, self).__init__()
    self.InterfaceList = {}
    self.ActivePortList = {}
    self.Unexport(objects=['Diagnostics'])
    self.Unexport(['ULAPrefix'])


class InternetGatewayDeviceFakeCPE(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  LANDeviceNumberOfEntries = tr.cwmptypes.NumberOf('LANDeviceList')
  WANDeviceNumberOfEntries = tr.cwmptypes.NumberOf('WANDeviceList')

  def __init__(self, device_id, periodic_stats=None):
    super(InternetGatewayDeviceFakeCPE, self).__init__()
    self.Unexport(params=['DeviceSummary'])
    self.Unexport(objects=['CaptivePortal', 'DeviceConfig',
                           'DownloadDiagnostics', 'IPPingDiagnostics',
                           'LANConfigSecurity', 'LANInterfaces',
                           'Layer2Bridging', 'Layer3Forwarding',
                           'QueueManagement', 'Services',
                           'TraceRouteDiagnostics', 'UploadDiagnostics',
                           'UserInterface'])
    self.Unexport(lists=['WANDevice'])
    self.LANDeviceList = {'1': LANDevice()}
    self.WANDeviceList = {}
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    self.Time = dm.igd_time.TimeTZ()
    self.Export(objects=['PeriodicStatistics'])
    if periodic_stats:
      self.PeriodicStatistics = periodic_stats


class LANDevice(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice.LANDevice for FakeCPE platforms."""

  def __init__(self):
    super(LANDevice, self).__init__()
    self.Unexport(['Alias'])
    self.Unexport(objects=['Hosts', 'LANHostConfigManagement'])
    self.Unexport(lists=['LANEthernetInterfaceConfig',
                         'LANUSBInterfaceConfig'])
    wifi = dm.fakewifi.FakeWifiWlanConfiguration()
    self.WLANConfigurationList = {'1': wifi}
    self.LANEthernetInterfaceList = {}
    self.LANUSBInterfaceList = {}

  LANWLANConfigurationNumberOfEntries = tr.cwmptypes.NumberOf(
      'WLANConfigurationList')
  LANEthernetInterfaceNumberOfEntries = tr.cwmptypes.NumberOf(
      'LANEthernetInterfaceList')
  LANUSBInterfaceNumberOfEntries = tr.cwmptypes.NumberOf(
      'LANUSBInterfaceList')


def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = InstallerFakeCPE
  params = list()
  objects = list()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceIdFakeCPE()
  device_model_root.Device = DeviceFakeCPE(devid, periodic_stats)
  objects.append('Device')
  device_model_root.InternetGatewayDevice = InternetGatewayDeviceFakeCPE(
      devid, periodic_stats)
  objects.append('InternetGatewayDevice')
  return (params, objects)


def main():
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceIdFakeCPE()
  device = DeviceFakeCPE(devid, periodic_stats)
  igd = InternetGatewayDeviceFakeCPE(devid, periodic_stats)
  tr.handle.Dump(device)
  tr.handle.Dump(igd)
  device.ValidateExports()
  igd.ValidateExports()
  print 'done'

if __name__ == '__main__':
  main()
