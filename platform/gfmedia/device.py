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
#pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fcntl
import os
import re
import subprocess
import google3
import dm.brcmmoca
import dm.brcmwifi
import dm.device_info
import dm.ethernet
import dm.igd_time
import dm.periodic_statistics
import dm.storage
import dm.temperature
import gfibertv
import platform_config
import pynetlinux
import stbservice
import tornado.ioloop
import tr.core
import tr.download
import tr.tr098_v1_2
import tr.tr181_v2_2 as tr181
import gvsb


BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
PYNETIFCONF = pynetlinux.ifconfig.Interface

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
CONFIGDIR = '/config/tr69'
DOWNLOADDIR = '/tmp'
GINSTALL = '/bin/ginstall.py'
HNVRAM = '/usr/bin/hnvram'
PROC_CPUINFO = '/proc/cpuinfo'
REBOOT = '/bin/tr69_reboot'
REPOMANIFEST = '/etc/repo-buildroot-manifest'
VERSIONFILE = '/etc/version'


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFMedia devices."""

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    return DOWNLOADDIR


class DeviceIdGFMedia(dm.device_info.DeviceIdMeta):
  def _GetOneLine(self, filename, default):
    try:
      f = open(filename, 'r')
      return f.readline().strip()
    except:
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
    if len(outlist) > 1 and len(outlist[1].strip()) > 0:
      return outlist[1].strip()
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
    return self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def Description(self):
    return 'Set top box for Google Fiber network'

  @property
  def SerialNumber(self):
    serial = self._GetNvramParam('1ST_SERIAL_NUMBER', default=None)
    if serial is None:
      serial = self._GetNvramParam('SERIAL_NO', default='000000000000')
    return serial

  @property
  def HardwareVersion(self):
    cpu = '?'
    with open(PROC_CPUINFO, 'r') as f:
      sys_re = re.compile('system type\s+: (\S+) STB platform')
      for line in f:
        stype = sys_re.search(line)
        if stype is not None:
          cpu = stype.group(1)
    return cpu

  @property
  def AdditionalHardwareVersion(self):
    return self._GetNvramParam('GPN', default='')

  @property
  def SoftwareVersion(self):
    return self._GetOneLine(VERSIONFILE, '0')

  @property
  def AdditionalSoftwareVersion(self):
    return self._GetOneLine(REPOMANIFEST, '')

  @property
  def ProductClass(self):
    return self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def ModemFirmwareVersion(self):
    return '0'


class InstallerGFMedia(tr.download.Installer):
  """Installer class used by tr/download.py."""

  def __init__(self, filename, ioloop=None):
    tr.download.Installer.__init__(self)
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
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

    cmd = [GINSTALL, '--tar={0}'.format(self.filename), '--partition=other']
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

  def on_stdout(self, fd, events):
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


class Services181GFMedia(tr181.Device_v2_2.Device.Services):
  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()
    self._AddStorageDevices()
    self.Export(lists=['STBService'])
    self.Export(['STBServiceNumberOfEntries'])
    self.STBServiceList = {'1': stbservice.STBService()}

  @property
  def STBServiceNumberOfEntries(self):
    return len(self.STBServiceList)

  def _AddStorageDevices(self):
    num = 0
    for drive in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
      try:
        if os.stat('/sys/block/' + drive):
          phys = dm.storage.PhysicalMediumDiskLinux26(drive, 'SATA/300')
          self.StorageServices.PhysicalMediumList[str(num)] = phys
          num = num + 1
      except OSError:
        pass

    num = 0
    for i in range(32):
      ubiname = 'ubi' + str(i)
      try:
        if os.stat('/sys/class/ubi/' + ubiname):
          ubi = dm.storage.FlashMediumUbiLinux26(ubiname)
          self.StorageServices.X_CATAWAMPUS_ORG_FlashMediaList[str(num)] = ubi
          num = num + 1
      except OSError:
        pass


class Ethernet181GFMedia(tr181.Device_v2_2.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for GFMedia platforms."""

  def __init__(self):
    tr181.Device_v2_2.Device.Ethernet.__init__(self)
    self.InterfaceList = {'1': dm.ethernet.EthernetInterfaceLinux26('eth0')}
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


class Moca181GFMedia(tr181.Device_v2_2.Device.MoCA):
  """Implementation of tr-181 Device.MoCA for GFMedia platforms."""

  def __init__(self):
    tr181.Device_v2_2.Device.MoCA.__init__(self)
    self.InterfaceList = {'1': dm.brcmmoca.BrcmMocaInterface('eth1')}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


class DeviceGFMedia(tr181.Device_v2_2.Device):
  """tr-181 Device implementation for Google Fiber media platforms."""

  def __init__(self, device_id, periodic_stats):
    tr181.Device_v2_2.Device.__init__(self)
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(objects='IP')
    self.Unexport(objects='LANConfigSecurity')
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
    self.Ethernet = Ethernet181GFMedia()
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.MoCA = Moca181GFMedia()
    self.Services = Services181GFMedia()
    self.InterfaceStackList = {}
    self.InterfaceStackNumberOfEntries = 0
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

    # GFHD100 & GFMS100 both monitor CPU temperature.
    # GFMS100 also monitors hard drive temperature.
    ts = self.DeviceInfo.TemperatureStatus
    ts.AddSensor(name="CPU temperature",
                 sensor=dm.temperature.SensorReadFromFile(
                     '/tmp/gpio/cpu_temperature'))
    for drive in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
      try:
        if os.stat('/sys/block/' + drive):
          ts.AddSensor(name='Hard drive temperature ' + drive,
                       sensor=dm.temperature.SensorHdparm(drive))
      except OSError:
        pass


class LANDeviceGFMedia(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice for Google Fiber media platforms."""

  def __init__(self):
    BASE98IGD.LANDevice.__init__(self)
    self.Unexport(objects='Hosts')
    self.Unexport(lists='LANEthernetInterfaceConfig')
    self.Unexport(objects='LANHostConfigManagement')
    self.Unexport(lists='LANUSBInterfaceConfig')
    self.LANEthernetInterfaceNumberOfEntries = 0
    self.LANUSBInterfaceNumberOfEntries = 0
    self.WLANConfigurationList = {}
    if self._has_wifi():
      wifi = dm.brcmwifi.BrcmWifiWlanConfiguration('eth2')
      self.WLANConfigurationList = {'1': wifi}

  def _has_wifi(self):
    try:
      PYNETIFCONF("eth2").get_index()
      return True
    except IOError:
      return False

  @property
  def LANWLANConfigurationNumberOfEntries(self):
    return len(self.WLANConfigurationList)


class InternetGatewayDeviceGFMedia(BASE98IGD):
  def __init__(self, device_id, periodic_stats):
    BASE98IGD.__init__(self)
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.LANDeviceList = {'1': LANDeviceGFMedia()}
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


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerGFMedia
  params = []
  objects = []
  dev_id = DeviceIdGFMedia()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  device_model_root.Device = DeviceGFMedia(dev_id, periodic_stats)
  device_model_root.InternetGatewayDevice = InternetGatewayDeviceGFMedia(
      dev_id, periodic_stats)
  device_model_root.X_GOOGLE_COM_GVSB = gvsb.Gvsb()
  tvrpc = gfibertv.GFiberTv('http://localhost:51834/xmlrpc')
  device_model_root.X_GOOGLE_COM_GFIBERTV = tvrpc
  objects.append('Device')
  objects.append('InternetGatewayDevice')
  objects.append('X_GOOGLE-COM_GVSB')
  objects.append('X_GOOGLE-COM_GFIBERTV')
  return (params, objects)


def main():
  dev_id = DeviceIdGFMedia()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  root = DeviceGFMedia(dev_id, periodic_stats)
  root.ValidateExports()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
