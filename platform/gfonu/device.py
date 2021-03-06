#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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
# Modified based on Denton's device.py for Bruno Platform
# pylint:disable=invalid-name

"""Data Model for GFiber ONU."""

__author__ = 'zixia@google.com (Ted Huang)'

# Modified based on gfmedia/device.py by Denton Gentry


import fcntl
import os
import subprocess
import traceback
import google3
import dm.device_info
import dm.ds6923_optical
import dm.ethernet
import dm.ghn
import dm.igd_time
import dm.mrvl88601_netstats
import dm.periodic_statistics
import dm.prestera
import dm.temperature
import platform_config
import pynetlinux
import tornado.ioloop
import tr.acs_config
import tr.basemodel
import tr.core
import tr.download
import tr.handle


PYNETIFCONF = pynetlinux.ifconfig.Interface

# File to find the name of the current running platform.  Override for test.
PLATFORM_FILE = '/etc/platform'

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
CONFIGDIR = '/fiber/config/tr69'
DOWNLOADDIR = '/tmp'
HNVRAM = 'hnvram'
HNVRAM_MTD = '/dev/mtd/hnvram'
SYSVAR = 'sysvar_cmd'
SYSVAR_ERROR = '<<ERROR CODE>>'
GINSTALL = 'ginstall'
LEDSTATUS = '/tmp/gpio/ledstate'
REBOOT = 'tr69_reboot'
MODELNAMEFILE = '/etc/platform'
HWVERSIONFILE = '/sys/devices/platform/board/hw_ver'
SWVERSIONFILE = '/etc/version'
REPOMANIFEST = '/etc/repo-buildroot-manifest'
GFLT110_OPTICAL_I2C_ADDR = 0x51
PON_STATS_DIR = '/sys/devices/platform/neta/anistats'
ETH_STATS_DIR = '/sys/devices/platform/neta/unistats'
KW2THERMALFILE = '/sys/devices/platform/KW2Thermal.0/temp1_input'
GFCH100THERMALFILE = '/sys/class/hwmon/hwmon0/temp1_input'


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFLT devices."""

  def __init__(self, ioloop=None):
    super(PlatformConfig, self).__init__()
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    return DOWNLOADDIR


class DeviceId(dm.device_info.DeviceIdMeta):
  """DeviceId for the GFLT devices."""

  def _GetOneLine(self, filename, default):
    """Get device statistics from file."""
    try:
      with open(filename, 'r') as f:
        out = f.readline().strip()
        if out and len(out) > 1:
          return out
        else:
          return default
    except IOError:
      return default

  def _GetNvramParam(self, param, default=''):
    """Return a parameter from NVRAM, like the serial number.

    Args:
      param: string name of the parameter to fetch. This must match the
        predefined names supported by /bin/hnvram
      default: value to return if the parameter is not present in NVRAM.

    Returns:
      A string value of the contents.
    """
    cmd = [HNVRAM, '-r', param]
    devnull = open('/dev/null', 'w')
    try:
      hnvram = subprocess.Popen(cmd, stdin=devnull, stderr=devnull,
                                stdout=subprocess.PIPE)
      out, _ = hnvram.communicate()
      if hnvram.returncode != 0:
        # Treat failure to run hnvram same as not having the field populated
        out = ''
    except OSError:
      out = ''
    outlist = out.strip().split('=')

    # HNVRAM does not distinguish between "value not present" and
    # "value present, and is empty." Treat empty values as invalid.
    if len(outlist) > 1 and outlist[1].strip():
      return outlist[1].strip()
    else:
      return default

  def _GetSysVarParam(self, param, default):
    """Get device statistics from SYSVAR partition."""

    cmd = [SYSVAR, '-g', param]
    devnull = open('/dev/null', 'w')

    try:
      getparam = subprocess.Popen(cmd, stdin=devnull, stderr=devnull,
                                  stdout=subprocess.PIPE)
      out, _ = getparam.communicate(None)
      if getparam.returncode != 0:
        out = ''
      if SYSVAR_ERROR in out.strip():
        out = ''
    except OSError:
      out = ''

    val = out.strip()
    if val and len(val) > 1:
      return val
    else:
      return default

  @property
  def Manufacturer(self):
    return 'Google Fiber'

  @property
  def ManufacturerOUI(self):
    return 'F88FCA'

  @property
  def ModelName(self):
    return self._GetOneLine(MODELNAMEFILE, default='UnknownModel')

  @property
  def Description(self):
    if IsPtp():
      return 'Point-To-Point Radio Device for Google Fiber network'
    return 'Optical Network Unit for Google Fiber network'

  @property
  def SerialNumber(self):
    if IsPtp():
      return self._GetNvramParam('1ST_SERIAL_NUMBER', default='000000000000')

    # GFLT300 uses HNVRAM and 1ST_SERIAL_NUMBER. Older model FJ's use sysvar,
    # differentiate the two by checking for the presence of '/dev/mtd/hnvram'
    if IsFiberJack() and os.path.exists(HNVRAM_MTD):
      return self._GetNvramParam('1ST_SERIAL_NUMBER', default='000000000000')
    return self._GetSysVarParam('SERIAL_NO', default='000000000000')

  @property
  def HardwareVersion(self):
    if IsPtp():
      return self._GetNvramParam('HW_VER', default='')
    return self._GetOneLine(HWVERSIONFILE, default='1.0')

  @property
  def AdditionalHardwareVersion(self):
    return self._GetSysVarParam('GPN', default='0.0')

  @property
  def SoftwareVersion(self):
    return self._GetOneLine(SWVERSIONFILE, default='1.0')

  @property
  def AdditionalSoftwareVersion(self):
    return self._GetOneLine(REPOMANIFEST, default='0.0')

  @property
  def ProductClass(self):
    return self._GetOneLine(MODELNAMEFILE, default='UnknownModel')

  @property
  def ModemFirmwareVersion(self):
    return '0'


class Installer(tr.download.Installer):
  """Control install of new software on device."""

  def __init__(self, url, ioloop=None):
    tr.download.Installer.__init__(self)
    self.url = url
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def Install(self, file_type, target_filename, callback):
    """Install self.url to system, then call callback."""
    print 'Installing: %r %r' % (file_type, target_filename)
    ftype = file_type.split()
    if ftype and ftype[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(ftype[0]))
      return False
    self._install_cb = callback

    cmd = [GINSTALL, '--once', '--tar=%s' % self.url, '--partition=other']
    try:
      self._ginstall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      print 'Failed to start ginstall: %s' % str(cmd)
      traceback.print_exc()
      return False

    fd = self._ginstall.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)
    return True

  def Reboot(self):
    cmd = [REBOOT]
    subprocess.call(cmd)

  def on_stdout(self, fd, unused_events):
    """Called whenever the ginstall process prints to stdout."""
    # drain the pipe
    inp = ''
    try:
      inp = os.read(fd, 4096)
    except OSError:   # returns EWOULDBLOCK
      pass
    if inp and inp.strip() != '.':
      print 'ginstall: %s' % inp.strip()
    if self._ginstall.poll() >= 0:
      self._ioloop.remove_handler(self._ginstall.stdout.fileno())
      if self._ginstall.returncode == 0:
        self._call_callback(0, '')
      else:
        print 'ginstall: exit code %d' % self._ginstall.poll()
        self._call_callback(INTERNAL_ERROR, 'Unable to install image.')


class EthernetInterfaceOnu(dm.ethernet.EthernetInterfaceLinux26):
  """Implementation of Device.Ethernet.Interface for the Onu.

  This just overrides the Stats property since getting stats for the ONU is
  slightly different.
  """

  def __init__(self, ifname, stat_dir, maxbitrate=0):
    super(EthernetInterfaceOnu, self).__init__(ifname=ifname,
                                               maxbitrate=maxbitrate)
    self.stat_dir = stat_dir

  @property
  def Stats(self):
    return dm.mrvl88601_netstats.NetdevStatsMrvl88601(stat_dir=self.stat_dir)


class Ethernet(tr.basemodel.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for gfonu platforms."""

  def __init__(self):
    tr.basemodel.Device.Ethernet.__init__(self)
    if IsPtp():
      self.InterfaceList = {
          '1': dm.ethernet.EthernetInterfaceLinux26(ifname='craft0'),
          '2': dm.ethernet.EthernetInterfaceLinux26(ifname='sw0'),
          '3': dm.prestera.EthernetInterfacePrestera(ifname='lan0'),
          '4': dm.prestera.EthernetInterfacePrestera(ifname='lan4'),
          '5': dm.prestera.EthernetInterfacePrestera(ifname='lan24'),
          '6': dm.prestera.EthernetInterfacePrestera(ifname='lan25'),
      }
    else:
      self.InterfaceList = {
          '1': EthernetInterfaceOnu('eth0', ETH_STATS_DIR),
          '2': EthernetInterfaceOnu('pon0', PON_STATS_DIR, maxbitrate=1000),
          '3': dm.ethernet.EthernetInterfaceLinux26(ifname='man'),
      }
    self.VLANTerminationList = {}
    self.LinkList = {}
    self.RMONStatsList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def VLANTerminationNumberOfEntries(self):
    return len(self.VLANTerminationList)

  @property
  def LinkNumberOfEntries(self):
    return len(self.LinkList)

  @property
  def RMONStatsNumberOfEntries(self):
    return len(self.RMONStatsList)


class Device(tr.basemodel.Device):
  """Device implementation for ONU device."""

  def __init__(self, device_id, periodic_stats):
    super(Device, self).__init__()
    self.Ethernet = Ethernet()
    self.Unexport(
        objects=['ATM', 'Bridging', 'BulkData', 'CaptivePortal',
                 'DHCPv4', 'DHCPv6', 'DLNA', 'DNS', 'DSL', 'DSLite',
                 'ETSIM2M', 'FaultMgmt', 'FAP', 'Firewall',
                 'GatewayInfo', 'HPNA', 'HomePlug', 'Hosts',
                 'IEEE8021x', 'IP', 'IPsec', 'IPv6rd', 'LANConfigSecurity',
                 'MoCA', 'NAT', 'NeighborDiscovery', 'PPP', 'PTM',
                 'QoS', 'RouterAdvertisement', 'Routing', 'Security',
                 'SelfTestDiagnostics', 'SmartCardReaders',
                 'SoftwareModules', 'Services',
                 'Time', 'UPA', 'UPnP', 'USB', 'UserInterface', 'Users',
                 'WiFi'])
    self.Unexport(lists=['InterfaceStack'])
    self.Unexport(['InterfaceStackNumberOfEntries', 'RootDataModelVersion'])

    with open(PLATFORM_FILE) as f:
      name = f.read().strip()

      if name == 'GFLT110' or name == 'GFLT120':
        self.Optical = dm.ds6923_optical.Ds6923Optical(GFLT110_OPTICAL_I2C_ADDR)
      else:
        self.Unexport(objects=['Optical'])

      if name == 'GFLT400':
        self.Ghn = dm.ghn.Ghn()
      else:
        self.Unexport(objects=['Ghn'])

    # DeficeInfo is defined under tr181.Device_v2_4,
    # not tr181.Device_v2_4.Device, so still need to Export here
    self.Export(objects=['DeviceInfo'])
    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.DeviceInfo.Unexport(lists=['Processor', 'SupportedDataModel',
                                    'VendorConfigFile', 'VendorLogFile'])
    self.DeviceInfo.Unexport(['LocationNumberOfEntries',
                              'ProcessorNumberOfEntries',
                              'VendorLogFileNumberOfEntries',
                              'VendorConfigFileNumberOfEntries',
                              'SupportedDataModelNumberOfEntries'])

    self.ManagementServer = tr.core.TODO()

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats
    led = dm.device_info.LedStatusReadFromFile('LED', LEDSTATUS)
    self.DeviceInfo.AddLedStatus(led)
    if IsPtp():
      self.DeviceInfo.TemperatureStatus.AddSensor(
          name='CPU temperature',
          # Armada thermal sensor reports milli-degrees C.
          sensor=dm.temperature.SensorReadFromFile(GFCH100THERMALFILE, 1000))
    else:
      self.DeviceInfo.TemperatureStatus.AddSensor(
          name='CPU temperature',
          # KW2 thermal sensor reports milli-degrees C.
          sensor=dm.temperature.SensorReadFromFile(KW2THERMALFILE, 1000))


class InternetGatewayDevice(tr.basemodel.InternetGatewayDevice):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.ManagementServer = tr.core.TODO()
    self.Unexport(params=['DeviceSummary', 'LANDeviceNumberOfEntries',
                          'WANDeviceNumberOfEntries', 'UserNumberOfEntries',
                          'SmartCardReaderNumberOfEntries'])
    self.Unexport(objects=['Capabilities', 'CaptivePortal', 'DeviceConfig',
                           'DLNA',
                           'DownloadAvailability',
                           'DownloadDiagnostics', 'FAP', 'FaultMgmt',
                           'Firewall',
                           'IPPingDiagnostics',
                           'LANConfigSecurity', 'LANInterfaces',
                           'Layer2Bridging', 'Layer3Forwarding',
                           'NSLookupDiagnostics',
                           'QueueManagement', 'Security',
                           'SelfTestDiagnostics',
                           'Services',
                           'SoftwareModules',
                           'TraceRouteDiagnostics', 'UploadDiagnostics',
                           'UDPEchoConfig',
                           'UPnP', 'USBHosts', 'UserInterface'])
    self.Unexport(lists=['LANDevice', 'WANDevice', 'User', 'SmartCardReader'])

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    self.DeviceInfo.Unexport(params=['VendorConfigFileNumberOfEntries'])

    self.Time = dm.igd_time.TimeTZ()

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats


def IsPlatform(platform_prefix):
  with open(PLATFORM_FILE) as f:
    if f.read().strip().startswith(platform_prefix):
      return True
  return False


def IsPtp():
  return IsPlatform('GFCH')


def IsFiberJack():
  return IsPlatform('GFLT')


# pylint:disable=unused-argument
def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = Installer
  params = []
  objects = []
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()

  device_model_root.Device = Device(dev_id, periodic_stats)
  objects.append('Device')
  device_model_root.InternetGatewayDevice = InternetGatewayDevice(
      dev_id, periodic_stats)
  objects.append('InternetGatewayDevice')

  return (params, objects)


def main():
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  root = Device(dev_id, periodic_stats)
  root.ValidateExports()
  tr.handle.Dump(root)

if __name__ == '__main__':
  main()
