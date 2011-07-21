#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Implementation of tr-181 Device.DeviceInfo object

"""

__author__ = 'dgentry@google.com (Denny Gentry)'

import xmlwitch

class DeviceInfoUno(object):
  def __init__(self, uptime, memory_info):
    self._manufacturer = "Google";
    self._manufacturer_oui = "00:1a:11:00:00:00"
    self._model_name = "Uno"
    self._description = "CPE device for Google Fiber network"
    self._serial_number = "00000000"
    self._hardware_version = "0"
    self._software_version = "0"

    self._uptime = uptime
    self._memory_info = memory_info

  def MemInfoToXml(self, xml):
    (totalmem, freemem) = self._memory_info.GetMemInfo()
    with xml.MemoryStatus:
      xml.Total(totalmem)
      xml.Free(freemem)
    return xml

  def ToXml(self, xml):
    with xml.DeviceInfo:
      xml.Manufacturer(self._manufacturer)
      xml.ManufacturerOUI(self._manufacturer_oui)
      xml.ModelName(self._model_name)
      xml.Description(self._description)
      xml.SerialNumber(self._serial_number)
      xml.HardwareVersion(self._hardware_version)
      xml.SoftwareVersion(self._software_version)
      xml.UpTime(self._uptime.GetUptime())
      self.MemInfoToXml(xml)
    return xml

class UptimeLinux26(object):
  def __init__(self):
    self._proc_uptime = "/proc/uptime"

  def GetUptime(self):
    """Returns a string of the number of seconds since the system booted.
    """
    try:
      uptime = float(open(self._proc_uptime).read().split()[0])
    except:
      # TODO(Dgentry) - LOG the exception, but return zeros by default
      uptime = 0.0
    return str(int(uptime))


class MemoryInfoLinux26(object):
  def __init__(self):
    self._proc_meminfo = "/proc/meminfo"

  def GetMemInfo(self):
    """Returns two strings (TotalMem, FreeMem)"""
    totalmem = 0
    freemem = 0
    try:
      pfile = open(self._proc_meminfo)
      for line in pfile:
        name, value, unit = line.split()
        if name == "MemTotal:":
          totalmem = int(value);
        elif name == "MemFree:":
          freemem = int(value);
    except:
      # TODO(Dgentry) - LOG the exception, but return zeros by default
      pass
    return (str(totalmem), str(freemem))


def main():
  ut = UptimeLinux26()
  mi = MemoryInfoLinux26()
  di = DeviceInfoUno(ut, mi)
  xml = xmlwitch.Builder(encoding='utf-8')
  print di.ToXml(xml)

if __name__ == '__main__':
  main()
