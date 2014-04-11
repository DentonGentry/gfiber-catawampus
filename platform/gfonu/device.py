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
# pylint: disable-msg=C6409

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
import dm.igd_time
import dm.mrvl88601_netstats
import dm.periodic_statistics
import dm.temperature
import platform_config
import pynetlinux
import tornado.ioloop
import tr.acs_config
import tr.core
import tr.download
import tr.tr181_v2_4 as tr181


BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
PYNETIFCONF = pynetlinux.ifconfig.Interface

# File to find the name of the current running platform.  Override for test.
PLATFORM_FILE = '/etc/platform'

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
CONFIGDIR = '/config/tr69'
DOWNLOADDIR = '/tmp'
SYSVAR = 'sysvar_cmd'
SYSVAR_ERROR = '<<ERROR CODE>>'
GINSTALL = 'ginstall.py'
REBOOT = 'tr69_reboot'
MODELNAMEFILE = '/etc/platform'
HWVERSIONFILE = '/sys/devices/platform/board/hw_ver'
SWVERSIONFILE = '/etc/version'
REPOMANIFEST = '/etc/repo-buildroot-manifest'
GFLT110_OPTICAL_I2C_ADDR = 0x51
PON_STATS_DIR = '/sys/devices/platform/neta/anistats'
ETH_STATS_DIR = '/sys/devices/platform/neta/unistats'
KW2THERMALFILE = '/sys/devices/platform/KW2Thermal.0/temp1_input'


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
    return 'Optical Network Unit for Google Fiber network'

  @property
  def SerialNumber(self):
    return self._GetSysVarParam('SERIAL_NO', default='000000000000')

  @property
  def HardwareVersion(self):
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
    print 'Installing: %r %r' % (file_type, target_filename)
    ftype = file_type.split()
    if ftype and ftype[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(ftype[0]))
      return False
    self._install_cb = callback

    if not os.path.exists(self.filename):
      self._call_callback(INTERNAL_ERROR,
                          'Installer: file %r does not exist.' % self.filename)
      return False

    # TODO(jnewlin): Remove the --skiploadersig once the new version of ginstall
    # is integrated down from the cpe2.0 branch.
    cmd = [GINSTALL, '--tar={0}'.format(self.filename), '--partition=other', 
           '--skiploadersig']
    try:
      self._ginstall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      return False

    fd = self._ginstall.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)
    return True

  def reboot(self):
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

  def __init__(self, ifname, stat_dir):
    super(EthernetInterfaceOnu, self).__init__(ifname=ifname)
    self.stat_dir = stat_dir

  @property
  def Stats(self):
    return dm.mrvl88601_netstats.NetdevStatsMrvl88601(stat_dir=self.stat_dir)


class Ethernet(tr181.Device_v2_4.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for gfonu platforms."""

  def __init__(self):
    tr181.Device_v2_4.Device.Ethernet.__init__(self)
    self.InterfaceList = {
        '1': EthernetInterfaceOnu('eth0', ETH_STATS_DIR),
        '2': EthernetInterfaceOnu('pon0', PON_STATS_DIR),
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


class Device(tr181.Device_v2_4.Device):
  """Device implementation for ONU device."""

  def __init__(self, device_id, periodic_stats):
    super(Device, self).__init__()
    self.Ethernet = Ethernet()
    self.Unexport(objects=['ATM', 'Bridging', 'CaptivePortal', 'DHCPv4',
                           'DHCPv6', 'DNS', 'DSL', 'DSLite', 'Firewall',
                           'GatewayInfo', 'Ghn', 'HPNA', 'HomePlug', 'Hosts',
                           'IEEE8021x', 'IP', 'IPv6rd', 'LANConfigSecurity',
                           'MoCA', 'NAT', 'NeighborDiscovery', 'PPP', 'PTM',
                           'QoS', 'RouterAdvertisement', 'Routing', 'Services',
                           'SmartCardReaders', 'UPA', 'USB', 'Users', 'WiFi'])
    self.Unexport(lists=['InterfaceStack'])
    self.Unexport(['InterfaceStackNumberOfEntries', 'RootDataModelVersion'])
    with open(PLATFORM_FILE) as f:
      if f.read().strip() == 'GFLT110':
        self.Optical = dm.ds6923_optical.Ds6923Optical(GFLT110_OPTICAL_I2C_ADDR)
      else:
        self.Unexport(objects=['Optical'])

    # DeficeInfo is defined under tr181.Device_v2_4,
    # not tr181.Device_v2_4.Device, so still need to Export here
    self.Export(objects=['DeviceInfo'])
    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.DeviceInfo.Unexport(lists=['X_CATAWAMPUS-ORG_LedStatus', 'Processor',
                                    'SupportedDataModel', 'VendorConfigFile',
                                    'VendorLogFile'])
    self.DeviceInfo.Unexport(['X_CATAWAMPUS-ORG_LedStatusNumberOfEntries',
                              'LocationNumberOfEntries',
                              'ProcessorNumberOfEntries',
                              'VendorLogFileNumberOfEntries',
                              'VendorConfigFileNumberOfEntries',
                              'SupportedDataModelNumberOfEntries'])

    self.ManagementServer = tr.core.TODO()

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats
    self.DeviceInfo.TemperatureStatus.AddSensor(
        name='CPU temperature',
        # KW2 thermal sensor reports milli-degrees C.
        sensor=dm.temperature.SensorReadFromFile(KW2THERMALFILE, 1000))


class InternetGatewayDevice(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.ManagementServer = tr.core.TODO()
    self.Unexport(params=['DeviceSummary', 'LANDeviceNumberOfEntries',
                          'WANDeviceNumberOfEntries'])
    self.Unexport(objects=['CaptivePortal', 'DeviceConfig',
                           'DownloadDiagnostics', 'IPPingDiagnostics',
                           'LANConfigSecurity', 'LANInterfaces',
                           'Layer2Bridging', 'Layer3Forwarding',
                           'QueueManagement', 'Services',
                           'TraceRouteDiagnostics', 'UploadDiagnostics',
                           'UserInterface'])
    self.Unexport(lists=['LANDevice', 'WANDevice'])

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    self.DeviceInfo.Unexport(params=['VendorConfigFileNumberOfEntries'])

    self.Time = dm.igd_time.TimeTZ()

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats


# pylint: disable-msg=unused-argument
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
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
