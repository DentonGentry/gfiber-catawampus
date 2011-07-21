#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Implementation of tr-181 Device.DeviceInfo object

"""

__author__ = 'dgentry@google.com (Denny Gentry)'

import collections
import glob
import os
import xmlwitch

# Used for Device.DeviceStatus.ProcessStatus.Process.{i}
Process = collections.namedtuple('Process', ['PID', 'Command', 'Size',
                                             'Priority', 'CPUTime', 'State'])

class DeviceInfoUno(object):
  def __init__(self, uptime, memory_info, process_status):
    self._manufacturer = "Google"
    self._manufacturer_oui = "00:1a:11:00:00:00"
    self._model_name = "Uno"
    self._description = "CPE device for Google Fiber network"
    self._serial_number = "00000000"
    self._hardware_version = "0"
    self._software_version = "0"

    self._uptime = uptime
    self._memory_info = memory_info
    self._process_status = process_status

  def _MemoryInfoToXml(self, xml):
    (totalmem, freemem) = self._memory_info.GetMemInfo()
    with xml.MemoryStatus:
      xml.Total(totalmem)
      xml.Free(freemem)
    return xml

  def _ProcessStatusToXml(self, xml):
    processes = self._process_status.GetProcesses()
    with xml.Process:
      for (num, proc) in enumerate(processes):
        with xml.__getitem__(str(num)):
          xml.PID(proc.PID)
          xml.Command(proc.Command)
          xml.Size(proc.Size)
          xml.Priority(proc.Priority)
          xml.CPUTime(proc.CPUTime)
          xml.State(proc.State)

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
      self._MemoryInfoToXml(xml)
      self._ProcessStatusToXml(xml)
    return xml

class UptimeLinux26(object):
  def __init__(self):
    self._proc_uptime = "/proc/uptime"

  def GetUptime(self):
    """Returns a string of the number of seconds since the system booted.
    """
    try:
      uptime = float(open(self._proc_uptime).read().split()[0])
    except IOError, KeyError:
      # TODO(Dgentry) - LOG the exception, but return zeros by default
      uptime = 0.0
    return str(int(uptime))


class MemoryInfoLinux26(object):
  def __init__(self):
    self._proc_meminfo = "/proc/meminfo"

  def GetMemInfo(self):
    """Returns two strings (TotalMem, FreeMem)"""
    totalmem = '0'
    freemem = '0'
    try:
      pfile = open(self._proc_meminfo)
      for line in pfile:
        fields = line.split()
        name = fields[0]
        value = fields[1]
        if name == "MemTotal:":
          totalmem = value
        elif name == "MemFree:":
          freemem = value
    except IOError, KeyError:
      # TODO(Dgentry) - LOG the exception, but return zeros by default
      pass
    return (totalmem, freemem)


class ProcessStatusLinux26(object):
  # Field ordering in /proc/<pid>/stat
  _PID = 0
  _COMM = 1
  _STATE = 2
  _UTIME = 13
  _STIME = 14
  _PRIO = 17
  _RSS = 23

  def __init__(self):
    tick = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    self._msec_per_jiffy = 1000 / tick
    self._slash_proc = "/proc"

  def _LinuxStateToTr181(self, linux_state):
    mapping = {
        "R" : "Running",
        "S" : "Sleeping",
        "D" : "Uninterruptible",
        "Z" : "Zombie",
        "T" : "Stopped",
        "W" : "Uninterruptible"}
    return mapping.get(linux_state, "Running")

  def _JiffiesToMsec(self, utime, stime):
    ticks = int(utime) + int(stime)
    msecs = ticks * self._msec_per_jiffy
    return str(msecs)

  def _RemoveParens(self, command):
    return command[1:-1]

  def GetProcesses(self):
    processes = list()
    for proc in glob.glob(self._slash_proc + "/[0123456789]*/stat"):
      try:
         fields = open(proc).read().split()
         p = Process(PID=fields[self._PID],
                     Command=self._RemoveParens(fields[self._COMM]),
                     Size=fields[self._RSS],
                     Priority=fields[self._PRIO],
                     CPUTime=self._JiffiesToMsec(fields[self._UTIME],
                                                 fields[self._STIME]),
                     State=self._LinuxStateToTr181(fields[self._STATE]))
         processes.append(p)
      except IOError:
        # This isn't an error. We have a list of files which existed the
        # moment the glog.glob was run. It a process exits before we get
        # around to reading it, its /proc file will go away.
        continue
      except KeyError:
        # TODO(dgentry) should LOG if exception is not IOError
        continue
    return processes


def main():
  ut = UptimeLinux26()
  mi = MemoryInfoLinux26()
  ps = ProcessStatusLinux26()
  di = DeviceInfoUno(ut, mi, ps)
  xml = xmlwitch.Builder(encoding='utf-8')
  print di.ToXml(xml)

if __name__ == '__main__':
  main()
