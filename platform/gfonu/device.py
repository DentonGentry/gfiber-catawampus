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
import dm.igd_time
import dm.periodic_statistics
import dm.temperature
import platform_config
import pynetlinux
import tornado.ioloop
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
SYSVAR = '/usr/bin/sysvar_cmd'
SYSVAR_ERROR = '<<ERROR CODE>>'
PRISMINSTALL = 'prisminstall.py'
PROC_CPUINFO = '/proc/cpuinfo'
REBOOT = 'tr69_reboot'
REPOMANIFEST = '/etc/repo-buildroot-manifest'
VERSIONFILE = '/etc/version'


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFLT devices."""

  def __init__(self, ioloop=None):
    super(PlatformConfig, self).__init__()
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    return DOWNLOADDIR


# TODO(zixia): based on real hardware chipset
class DeviceId(dm.device_info.DeviceIdMeta):
  """DeviceId for the GFLT devices."""

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
    return self._GetSysVarParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def Description(self):
    return 'Optical Network Unit for Google Fiber network'

  @property
  def SerialNumber(self):
    return self._GetSysVarParam('SERIAL_NO', default='666666666666')

  @property
  def HardwareVersion(self):
    return self._GetSysVarParam('HW_REV', default='1.0')

  @property
  def AdditionalHardwareVersion(self):
    return self._GetSysVarParam('GPN', default='0.0')

  @property
  def SoftwareVersion(self):
    return self._GetSysVarParam('SW_REV', default='1.0')

  @property
  def AdditionalSoftwareVersion(self):
    return self._GetSysVarParam('REPOMANIFEST', default='0.0')

  @property
  def ProductClass(self):
    return self._GetSysVarParam('PLATFORM_NAME', default='UnknownModel')

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

    cmd = [PRISMINSTALL, '--tar={0}'.format(self.filename)]
    try:
      self._prisminstall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      return False

    fd = self._prisminstall.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)
    return True

  def reboot(self):
    cmd = [REBOOT]
    subprocess.call(cmd)

  def on_stdout(self, fd, unused_events):
    """Called whenever the prisminstall process prints to stdout."""
    # drain the pipe
    inp = ''
    try:
      inp = os.read(fd, 4096)
    except OSError:   # returns EWOULDBLOCK
      pass
    if inp and inp.strip() != '.':
      print 'prisminstall: %s' % inp.strip()
    if self._prisminstall.poll() >= 0:
      self._ioloop.remove_handler(self._prisminstall.stdout.fileno())
      if self._prisminstall.returncode == 0:
        self._call_callback(0, '')
      else:
        print 'prisminstall: exit code %d' % self._prisminstall.poll()
        self._call_callback(INTERNAL_ERROR, 'Unable to install image.')


class Device(tr181.Device_v2_4.Device):
  """Device implementation for ONU device."""

  def __init__(self, device_id, periodic_stats):
    super(Device, self).__init__()
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DHCPv6')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='DSLite')
    self.Unexport(objects='Ethernet')
    self.Unexport(objects='Firewall')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='Ghn')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(lists='InterfaceStack')
    self.Unexport('InterfaceStackNumberOfEntries')
    self.Unexport(objects='IP')
    self.Unexport(objects='IPv6rd')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(objects='ManagementServer')
    self.Unexport(objects='MoCA')
    self.Unexport(objects='NAT')
    self.Unexport(objects='NeighborDiscovery')
    self.Unexport(objects='PPP')
    self.Unexport(objects='PTM')
    self.Unexport(objects='QoS')
    self.Unexport('RootDataModelVersion')
    self.Unexport(objects='RouterAdvertisement')
    self.Unexport(objects='Routing')
    self.Unexport(objects='Services')
    self.Unexport(objects='SmartCardReaders')
    self.Unexport(objects='UPA')
    self.Unexport(objects='USB')
    self.Unexport(objects='Users')
    self.Unexport(objects='WiFi')
    with open(PLATFORM_FILE) as f:
      if f.read().strip() == 'GFLT110':
        self.Optical = dm.ds6923_optical.Ds6923Optical()

    # DeficeInfo is defined under tr181.Device_v2_4,
    # not tr181.Device_v2_4.Device, so still need to Export here
    self.Export(objects=['DeviceInfo'])
    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.DeviceInfo.Unexport('X_CATAWAMPUS-ORG_LedStatusNumberOfEntries')
    self.DeviceInfo.Unexport(lists='X_CATAWAMPUS-ORG_LedStatus')
    self.DeviceInfo.Unexport('LocationNumberOfEntries')
    self.DeviceInfo.Unexport(lists='Processor')
    self.DeviceInfo.Unexport(lists='SupportedDataModel')
    self.DeviceInfo.Unexport(lists='VendorConfigFile')
    self.DeviceInfo.Unexport(lists='VendorLogFile')
    self.DeviceInfo.Unexport('ProcessorNumberOfEntries')
    self.DeviceInfo.Unexport('VendorLogFileNumberOfEntries')
    self.DeviceInfo.Unexport('VendorConfigFileNumberOfEntries')
    self.DeviceInfo.Unexport('SupportedDataModelNumberOfEntries')

    self.ManagementServer = tr.core.TODO()

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats


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
    self.Unexport(objects='LANInterfaces')
    self.Unexport(objects='Layer2Bridging')
    self.Unexport(objects='Layer3Forwarding')
    self.ManagementServer = tr.core.TODO()
    self.Unexport(objects='QueueManagement')
    self.Unexport(objects='Services')
    self.Unexport(objects='TraceRouteDiagnostics')
    self.Unexport(objects='UploadDiagnostics')
    self.Unexport(objects='UserInterface')
    self.Unexport(lists='LANDevice')
    self.Unexport(lists='WANDevice')
    self.Unexport(params='LANDeviceNumberOfEntries')
    self.Unexport(params='WANDeviceNumberOfEntries')

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    self.DeviceInfo.Unexport(params='VendorConfigFileNumberOfEntries')

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
