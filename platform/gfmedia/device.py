#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import device_info
import ethernet
import fcntl
import management_server
import os
import subprocess
import tr.core
import tr.download
import tr.soap
import tr.tornadi_fix
import tr.tornado.ioloop
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


class DeviceIdGFMedia(object):
  def __init__(self):
    self.Manufacturer = 'Google'
    self.ManufacturerOUI = '001a11'
    self.ModelName = GetNvramParam("PRODUCT_NAME", default="UnknownModel")
    self.Description = 'Set top box for Google Fiber network'
    self.SerialNumber = GetNvramParam("SERIAL_NO", default="000000000000")
    self.HardwareVersion = '0'
    self.AdditionalHardwareVersion = '0'
    self.SoftwareVersion = '0'
    self.AdditionalSoftwareVersion = '0'
    self.ProductClass = 'STB'


class DeviceInfoGFMedia(device_info.DeviceInfoLinux26):
  def __init__(self):
    device_info.DeviceInfoLinux26.__init__(self, DeviceIdGFMedia())


GINSTALL = "/bin/ginstall.py"
REBOOT = "/bin/tr69_reboot"
class InstallerGFMedia(tr.download.Installer):
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
    self.ATM = tr.core.TODO()
    self.Bridging = tr.core.TODO()
    self.CaptivePortal = tr.core.TODO()
    self.DHCPv4 = tr.core.TODO()
    self.DNS = tr.core.TODO()
    self.DSL = tr.core.TODO()
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

    # One Ethernet port, Wifi, and MoCA
    self.Ethernet = ethernet.Ethernet()
    self.Ethernet.AddInterface("eth0", False, ethernet.EthernetInterfaceLinux26)

    self.ManagementServer = management_server.ManagementServer()


def PlatformInit(name, device_model_root):
  tr.download.INSTALLER = InstallerGFMedia
  tr.download.SetStateDir("/config/tr69_dnld/")
  params = []
  objects = []
  device_model_root.Device = DeviceGFMedia()
  objects.append('Device')
  device_model_root.DeviceInfo = DeviceInfoGFMedia()
  objects.append('DeviceInfo')
  return (params, objects)


def main():
  root = DeviceGFMedia()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
