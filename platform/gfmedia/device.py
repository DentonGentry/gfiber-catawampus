#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import dm.device_info
import fcntl
import os
import subprocess
import tornado.ioloop
import tr.core
import tr.download
import tr.soap
import tr.tr181_v2_2 as tr181


# tr-69 error codes
INTERNAL_ERROR = 9002


HNVRAM = '/bin/hnvram'
def GetNvramParam(param, default=""):
  """Return a parameter from NVRAM, like the serial number.
  Args:
    param: string name of the parameter to fetch. This must match the
      predefined names supported by /bin/hnvram
    default: value to return if the parameter is not present in NVRAM.

  Returns:
    A string value of the contents.
  """
  cmd = [HNVRAM, "-r", param]
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


def GetOneLine(filename, default):
  try:
    f = open(filename, 'r')
    return f.readline().strip()
  except:
    return default


VERSIONFILE = '/etc/version'
REPOMANIFEST = '/etc/repo-buildroot-manifest'

class DeviceIdGFMedia(object):
  def __init__(self):
    self.Manufacturer = 'Google'
    self.ManufacturerOUI = '001a11'
    self.ModelName = GetNvramParam("PRODUCT_NAME", default="UnknownModel")
    self.Description = 'Set top box for Google Fiber network'
    self.SerialNumber = GetNvramParam("SERIAL_NO", default="000000000000")
    self.HardwareVersion = '0'
    self.AdditionalHardwareVersion = '0'
    self.SoftwareVersion = GetOneLine(VERSIONFILE, '0.0.0')
    self.AdditionalSoftwareVersion = GetOneLine(REPOMANIFEST, '')
    self.ProductClass = 'STB'


class DeviceInfoGFMedia(dm.device_info.DeviceInfoLinux26):
  def __init__(self):
    device_info.DeviceInfoLinux26.__init__(self, DeviceIdGFMedia())


GINSTALL = "/bin/ginstall.py"
REBOOT = "/bin/tr69_reboot"
class InstallerGFMedia(tr.download.Installer):
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
    cmd = [GINSTALL, "--tar={0}".format(self.filename), "--partition=other"]
    devnull = open('/dev/null', 'w')
    try:
      self._ginstall = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=devnull)
    except OSError:
      self._call_callback(INTERNAL_ERROR, "Unable to start installer process")
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


class DeviceGFMedia(tr181.Device_v2_2.Device):
  """Device implementation for Google Fiber media platforms."""

  def __init__(self):
    tr181.Device_v2_2.Device.__init__(self)
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
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
    self.Unexport(objects='MoCA')
    self.Unexport(objects='NAT')
    self.Unexport(objects='PPP')
    self.Unexport(objects='PTM')
    self.Unexport(objects='QoS')
    self.Unexport(objects='Routing')
    self.Unexport(objects='Services')
    self.Unexport(objects='SmartCardReaders')
    self.Unexport(objects='UPA')
    self.Unexport(objects='USB')
    self.Unexport(objects='Users')

    self.DeviceInfo = DeviceInfoGFMedia()
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.Ethernet = tr.core.TODO()
    self.InterfaceStackNumberOfEntries = 0


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerGFMedia
  tr.download.SetStateDir("/config/tr69_dnld/")
  params = []
  objects = []
  device_model_root.Device = DeviceGFMedia()
  objects.append('Device')
  return (params, objects)


def main():
  root = DeviceGFMedia()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
