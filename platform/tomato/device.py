#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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
# pylint: disable-msg=C6409

"""Device Models for TomatoUSB."""

__author__ = 'zve@google.com (Alexei Zverovitch)'

import fcntl
import os
import subprocess
import google3
import dm.device_info
import dm.ethernet
import dm.igd_time
import dm.ipinterface
import dm.periodic_statistics
import dm.storage
import dm.traceroute
import platform_config
import tornado.ioloop
import tr.acs_config
import tr.core
import tr.download
import tr.tr181_v2_2 as tr181
import tr.x_catawampus_tr181_2_0


BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
CATA181 = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0

# tr-69 error codes
INTERNAL_ERROR = 9002

# tr-69 file types
FILETYPE_FIRMWARE_IMAGE = '1 Firmware Upgrade Image'
FILETYPE_JFFS_IMAGE = 'X 001A11 JFFS Upgrade Image'  # 001A11 is Google Inc.

# Unit tests can override these with fake data
NVRAM = 'nvram'
REBOOT = 'reboot'
INSTALL_FIRMWARE_IMAGE = 'install_firmware'
INSTALL_JFFS_IMAGE = 'install_jffs'
JFFS_VERSION_FILE = '/jffs/jffs-version.txt'
CONFIGDIR = '/config/tr69'
DOWNLOADDIR = '/mnt/share/download'


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFMedia devices."""

  # pylint: disable-msg=unused-argument
  def __init__(self, ioloop=None):
    super(PlatformConfig, self).__init__()

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    return DOWNLOADDIR


class Installer(tr.download.Installer):
  """Installer for Tomato and JFFS images."""

  def __init__(self, filename, ioloop=None):
    tr.download.Installer.__init__(self)
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
    """Install self.filename to disk, then call callback."""
    self._install_cb = callback
    print 'Installing: %r %r' % (file_type, target_filename)
    if file_type == FILETYPE_FIRMWARE_IMAGE:
      installer_cmd = INSTALL_FIRMWARE_IMAGE
    elif file_type == FILETYPE_JFFS_IMAGE:
      installer_cmd = INSTALL_JFFS_IMAGE
    else:
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(file_type))
      return False

    if not os.path.exists(self.filename):
      self._call_callback(INTERNAL_ERROR,
                          'Installer: file %r does not exist.' % self.filename)
      return False

    cmd = [installer_cmd, self.filename]
    try:
      self._install = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      return False

    fd = self._install.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)
    return True

  def reboot(self):
    cmd = [REBOOT]
    subprocess.call(cmd)

  def on_stdout(self, fd, unused_events):
    """Called whenever the install process prints to stdout."""
    # drain the pipe
    inp = ''
    try:
      inp = os.read(fd, 4096)
    except OSError:   # returns EWOULDBLOCK
      pass
    if inp and inp.strip() != '.':
      print 'install: %s' % inp.strip()
    if self._install.poll() >= 0:
      self._ioloop.remove_handler(self._install.stdout.fileno())
      if self._install.returncode == 0:
        self._call_callback(0, '')
      else:
        print 'install: exit code %d' % self._install.poll()
        self._call_callback(INTERNAL_ERROR, 'Unable to install image.')


class DeviceId(dm.device_info.DeviceIdMeta):
  """Parameters for the DeviceInfo object for a TomatoUSB platform."""

  @staticmethod
  def _GetOneLine(filename, default):
    """Read one line from file.

    Args:
      filename: the name of the file to read.
      default: the value to return if the file can't be read.

    Returns:
      The first line of the file, with leading and trailing whitespaces
      removed.
    """
    try:
      with open(filename, 'r') as f:
        return f.readline().strip()
    except IOError:
      return default

  @staticmethod
  def _GetNvramParam(param, default=''):
    """Return a parameter from NVRAM, like the serial number.

    Args:
      param: string name of the parameter to fetch.
      default: value to return if the parameter is not present in NVRAM.

    Returns:
      A string value of the contents.
    """
    cmd = [NVRAM, 'get', param]
    with open('/dev/null', 'w') as devnull:
      out = ''
      try:
        nvram = subprocess.Popen(cmd, stdin=devnull, stderr=devnull,
                                 stdout=subprocess.PIPE)
        out, _ = nvram.communicate()
        if nvram.returncode != 0:
          # Treat failure to run nvram same as not having the field populated
          out = ''
      except OSError:
        out = ''
    return out.strip() or default

  @property
  def Manufacturer(self):
    return DeviceId._GetNvramParam('wps_mfstring',
                                   default='Unknown manufacturer')

  @property
  def ManufacturerOUI(self):
    return '001A11'  # Google Inc.

  @property
  def ModelName(self):
    return DeviceId._GetNvramParam('wps_modelnum',
                                   default='Unknown TomatoUSB device')

  @property
  def Description(self):
    return 'TomatoUSB device'

  @property
  def SerialNumber(self):
    return DeviceId._GetNvramParam('et0macaddr',
                                   default='00:00:00:00:00:00')

  @property
  def HardwareVersion(self):
    return DeviceId._GetNvramParam('hardware_version', default='')

  @property
  def AdditionalHardwareVersion(self):
    return ''

  @property
  def SoftwareVersion(self):
    return DeviceId._GetNvramParam('buildno', default='')

  @property
  def AdditionalSoftwareVersion(self):
    return DeviceId._GetOneLine(JFFS_VERSION_FILE, default='')

  @property
  def ProductClass(self):
    return DeviceId._GetNvramParam('wps_modelnum', default='Generic_TomatoUSB')

  @property
  def ModemFirmwareVersion(self):
    return ''


class Services(tr181.Device_v2_2.Device.Services):
  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()


class Device(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  def __init__(self, device_id, periodic_stats):
    super(Device, self).__init__()
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DHCPv6')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='DSLite')
    self.Unexport(objects='Firewall')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(objects='IPv6rd')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(objects='NAT')
    self.Unexport(objects='NeighborDiscovery')
    self.Unexport(objects='PPP')
    self.Unexport(objects='PTM')
    self.Unexport(objects='QoS')
    self.Unexport(objects='RouterAdvertisement')
    self.Unexport(objects='Routing')
    self.Unexport(objects='SmartCardReaders')
    self.Unexport(objects='UPA')
    self.Unexport(objects='USB')
    self.Unexport(objects='Users')
    self.Unexport(objects='WiFi')

    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.ManagementServer = tr.core.TODO()  # Higher layer code splices this in
    self.Services = Services()

    self.InterfaceStackNumberOfEntries = 0
    self.InterfaceStackList = {}

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

    self.Ethernet = Ethernet()
    self.IP = IP()
    self.MoCA = MoCA()


class Ethernet(tr181.Device_v2_2.Device.Ethernet):
  """Implements Device_v2_2.Device.Ethernet for TomatoUSB platform."""

  def __init__(self):
    super(Ethernet, self).__init__()
    self.InterfaceList = {
# TODO(zve): figure out what's causing the SchemaError and put these back in
#            (root.Ethernet.Interface.Status is exported but does not exist)
#
#        '1': dm.ethernet.EthernetInterfaceLinux26(ifname='eth0'),
#        '256': dm.ethernet.EthernetInterfaceLinux26(ifname='br0')
    }
    self.VLANTerminationList = {}
    self.LinkList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def VLANTerminationNumberOfEntries(self):
    return len(self.VLANTerminationList)

  @property
  def LinkNumberOfEntries(self):
    return len(self.LinkList)


class IP(tr181.Device_v2_2.Device.IP):
  """Implements Device_v2_2.Device.IP for TomatoUSB Platform."""

  # Enable fields are supposed to be writeable; we don't support that.
  IPv4Capable = tr.types.ReadOnlyBool(True)
  IPv4Enable = tr.types.ReadOnlyBool(True)
  IPv4Status = tr.types.ReadOnlyString('Enabled')
  IPv6Capable = tr.types.ReadOnlyBool(False)
  IPv6Enable = tr.types.ReadOnlyBool(False)
  IPv6Status = tr.types.ReadOnlyString('Disabled')

  def __init__(self):
    super(IP, self).__init__()
    self.Unexport('ULAPrefix')
    self.InterfaceList = {
# TODO(zve): figure out what's causing the SchemaError and put these back in
#            (root.IP.Interface.Status is exported but does not exist)
#
#        1: dm.ipinterface.IPInterfaceLinux26(
#            ifname='eth0', lowerlayers='Device.Ethernet.Interface.1'),
#        256: dm.ipinterface.IPInterfaceLinux26(
#            ifname='br0', lowerlayers='Device.Ethernet.Interface.256')
    }
    self.ActivePortList = {}
    self.Diagnostics = IPDiagnostics()

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def ActivePortNumberOfEntries(self):
    return len(self.ActivePortList)


class MoCA(tr181.Device_v2_2.Device.MoCA):
  """Implements Device_v2_2.Device.MoCA for TomatoUSB Platform."""

  def __init__(self):
    super(MoCA, self).__init__()
    self.InterfaceNumberOfEntries = 0
    self.InterfaceList = {}


class InternetGatewayDevice(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.LANDeviceList = {'1': LANDevice()}
    self.Unexport(objects='LANInterfaces')
    self.Unexport(objects='Layer2Bridging')
    self.Unexport(objects='Layer3Forwarding')
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.Unexport(objects='QueueManagement')
    self.Unexport(objects='Services')
    self.Unexport(objects='TraceRouteDiagnostics')
    self.Unexport(objects='UploadDiagnostics')
    self.Unexport(objects='UserInterface')
    self.Unexport(lists='WANDevice')

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    self.Time = dm.igd_time.TimeTZ()
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

  @property
  def LANDeviceNumberOfEntries(self):
    return len(self.LANDeviceList)

  @property
  def WANDeviceNumberOfEntries(self):
    return 0


class LANDevice(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice for TomatoUSB platforms."""

  def __init__(self):
    super(LANDevice, self).__init__()
    self.Unexport('Alias')
    self.Unexport(objects='Hosts')
    self.Unexport(lists='LANEthernetInterfaceConfig')
    self.Unexport(objects='LANHostConfigManagement')
    self.Unexport(lists='LANUSBInterfaceConfig')
    self.WLANConfigurationList = {}

  @property
  def LANWLANConfigurationNumberOfEntries(self):
    return len(self.WLANConfigurationList)

  @property
  def LANEthernetInterfaceNumberOfEntries(self):
    return 0

  @property
  def LANUSBInterfaceNumberOfEntries(self):
    return 0


class IPDiagnostics(CATA181.Device.IP.Diagnostics):
  """tr-181 Device.IP.Diagnostics for Google Fiber media platforms."""

  def __init__(self):
    super(IPDiagnostics, self).__init__()
    self.Unexport(objects='IPPing')
    self.Unexport(objects='X_CATAWAMPUS-ORG_Speedtest')
    self.TraceRoute = dm.traceroute.TraceRoute()


# pylint: disable-msg=unused-argument
def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = Installer
  params = list()
  objects = list()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceId()
  device_model_root.Device = Device(devid, periodic_stats)
  objects.append('Device')
  device_model_root.InternetGatewayDevice = InternetGatewayDevice(
      devid, periodic_stats)
  objects.append('InternetGatewayDevice')
  return (params, objects)


def main():
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceId()
  device = Device(devid, periodic_stats)
  igd = InternetGatewayDevice(devid, periodic_stats)
  tr.core.Dump(device)
  tr.core.Dump(igd)
  device.ValidateExports()
  igd.ValidateExports()
  print 'done'

if __name__ == '__main__':
  main()
