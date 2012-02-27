#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fcntl
import os
import subprocess
import google3
import dm.brcmwifi
import dm.device_info
import dm.storage
import platform_config
import tornado.ioloop
import tr.core
import tr.download
import tr.tr098_v1_2 as tr98
import tr.tr181_v2_2 as tr181
import gvsb


# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
CONFIGDIR = '/config/tr69'
DOWNLOADDIR = '/rw/tr69'
GINSTALL = '/bin/ginstall.py'
HNVRAM = '/bin/hnvram'
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
      out, err = hnvram.communicate()
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
    return 'f88fca'

  @property
  def ModelName(self):
    return self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def Description(self):
    return 'Set top box for Google Fiber network'

  @property
  def SerialNumber(self):
    return self._GetNvramParam('1ST_SERIAL_NUMBER', default='000000000000')

  @property
  def HardwareVersion(self):
    return '0'  # TODO

  @property
  def AdditionalHardwareVersion(self):
    return '0'  # TODO

  @property
  def SoftwareVersion(self):
    return self._GetOneLine(VERSIONFILE, '0.0.0')

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
  """Installer class used by tr/download.py"""
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
                          'Unsupported file_type {0}'.format(type[0]))
      return False
    self._install_cb = callback
    cmd = [GINSTALL, '--tar={0}'.format(self.filename), '--partition=other']
    devnull = open('/dev/null', 'w')
    try:
      self._ginstall = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=devnull)
    except OSError:
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      return False
    fd = self._ginstall.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)

  def reboot(self):
    cmd = [REBOOT]
    subprocess.call(cmd)

  def on_stdout(self, fd, events):
    """Called whenever the ginstall process prints to stdout."""
    # drain the pipe
    try:
      os.read(fd, 4096)
    except OSError:   # returns EWOULDBLOCK
      pass
    if self._ginstall.poll() >= 0:
      self._ioloop.remove_handler(self._ginstall.stdout.fileno())
      if self._ginstall.returncode == 0:
        self._call_callback(0, '')
      else:
        self._call_callback(INTERNAL_ERROR, 'Unable to install image.')


class Services181GFMedia(tr181.Device_v2_2.Device.Services):
  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()

    for drive in ['sda', 'sdb', 'sdc', 'sdd']:
      try:
        if os.stat('/sys/block/' + drive):
          phys = dm.storage.PhysicalMediumDiskLinux26(drive, 'SATA/300')
          self.StorageServices.PhysicalMediumList['0'] = phys
      except OSError:
        pass


class DeviceGFMedia(tr181.Device_v2_2.Device):
  """tr-181 Device implementation for Google Fiber media platforms."""

  def __init__(self, device_id):
    tr181.Device_v2_2.Device.__init__(self)
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
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.Services = Services181GFMedia()
    self.InterfaceStackList = {}
    self.InterfaceStackNumberOfEntries = 0


BASE98IGD = tr98.InternetGatewayDevice_v1_4.InternetGatewayDevice

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
    wifi = dm.brcmwifi.BrcmWifiWlanConfiguration('eth2')
    self.WLANConfigurationList = {'0' : wifi}

  @property
  def LANWLANConfigurationNumberOfEntries(self):
    return len(self.WLANConfigurationList)


class InternetGatewayDeviceGFMedia(BASE98IGD):
  def __init__(self, device_id):
    BASE98IGD.__init__(self)
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.LANDeviceList = {'0' : LANDeviceGFMedia() }
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
    return len(self.LANDeviceList)

  @property
  def WANDeviceNumberOfEntries(self):
    return 0


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerGFMedia
  params = []
  objects = []
  dev_id = DeviceIdGFMedia()
  device_model_root.Device = DeviceGFMedia(dev_id)
  device_model_root.InternetGatewayDevice = InternetGatewayDeviceGFMedia(dev_id)
  device_model_root.X_GOOGLE_COM_GVSB = gvsb.Gvsb()
  objects.append('Device')
  objects.append('InternetGatewayDevice')
  objects.append('X_GOOGLE-COM_GVSB')
  return (params, objects)


def main():
  root = DeviceGFMedia()
  root.ValidateExports()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
