#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Implementation of tr-181 Device.DeviceInfo object

Handles the Device.DeviceInfo portion of TR-181, as described
by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import glob
import os
import tr.core
import tr.tr181_v2_2 as tr181
import xmlwitch

BaseDevice = tr181.Device_v2_2


class DeviceInfo(BaseDevice.DeviceInfo):
  """Outputs fields to Device.DeviceInfo specific to the Google Uno platform.

  This object handles the manufacturer name, OUI, model, serial number,
  hardware and software versions, etc.
  """
  def __init__(self):
    BaseDevice.DeviceInfo.__init__(self)
    self.Manufacturer = "Google"
    self.ManufacturerOUI = "00:1a:11:00:00:00"
    self.ModelName = "Uno"
    self.Description = "CPE device for Google Fiber network"
    self.SerialNumber = "00000000"
    self.HardwareVersion = "0"
    self.AdditionalHardwareVersion = "0"
    self.SoftwareVersion = "0"
    self.AdditionalSoftwareVersion = "0"
    self.GetUptime = UptimeLinux26().GetUptime
    self.MemoryStatus = MemoryStatusLinux26()
    self.ProcessStatus = ProcessStatusLinux26()
    self.ProvisioningCode = None  # TODO(apenwarr): fill me
    self.ProductClass = 'Uno'
    self.FirstUseDate = None  # TODO(apenwarr): fill me
    self.ProcessorNumberOfEntries = 0
    self.VendorConfigFileNumberOfEntries = 0
    self.VendorLogFileNumberOfEntries = 0
    self.SupportedDataModelNumberOfEntries = 0
    self.NetworkProperties = self.NetworkProperties()
    self.NetworkProperties.MaxTCPWindowSize = 0,  # TODO(apenwarr): fill me
    self.NetworkProperties.TCPImplementation = '' # TODO(apenwarr): fill me
    self.TemperatureStatus = self.TemperatureStatus()
    self.TemperatureStatus.TemperatureSensorNumberOfEntries = 0
    self.TemperatureStatus.TemperatureSensorList = {}
    self.VendorLogFileList = {}
    self.VendorConfigFileList = {}
    self.SupportedDataModelList = {}
    self.ProcessorList = {}

  @property
  def UpTime(self):
      return self.GetUptime()


class UptimeLinux26(object):
  """Abstraction to get uptime in seconds from the underlying platform.

  Reads /proc/uptime to get a floating point number of seconds since boot.
  Returns this as a string of the integer number of seconds, which is what
  TR-181 needs.

  Tests can set _proc_uptime to a file with fake data, instead of /proc/uptime.
  """
  def __init__(self):
    self._proc_uptime = "/proc/uptime"

  def GetUptime(self):
    """Returns a string of the number of seconds since the system booted.
    """
    try:
      uptime = float(open(self._proc_uptime).read().split()[0])
    except IOError, KeyError:
      # TODO(dgentry) - LOG the exception, but return zeros by default
      uptime = 0.0
    return str(int(uptime))


class MemoryStatusLinux26(BaseDevice.DeviceInfo.MemoryStatus):
  """Abstraction to get memory information from the underlying platform.

  Reads proc/meminfo to find TotalMem and FreeMem.

  Tests can set _proc_meminfo to a file with fake data instead of /proc/meminfo
  """
  def __init__(self):
    BaseDevice.DeviceInfo.MemoryStatus.__init__(self)
    self._proc_meminfo = "/proc/meminfo"

  @property
  def Total(self):
      return int(self.GetMemInfo()[0])

  @property
  def Free(self):
      return int(self.GetMemInfo()[1])

  def GetMemInfo(self):
    """Fetch TotalMem and FreeMem from the underlying platform.

    Args: None

    Returns: a list of two strings, (totalmem, freemem)
    """
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


class ProcessStatusLinux26(BaseDevice.DeviceInfo.ProcessStatus):
  """Abstraction to get information about running processes from the
  underlying platform.

  Reads /proc/<pid> to get information about processes.

  Tests can set _slash_proc to a directory structure with fake data.
  """
  # Field ordering in /proc/<pid>/stat
  _PID = 0
  _COMM = 1
  _STATE = 2
  _UTIME = 13
  _STIME = 14
  _PRIO = 17
  _RSS = 23

  def __init__(self):
    BaseDevice.DeviceInfo.ProcessStatus.__init__(self)
    tick = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    self._msec_per_jiffy = 1000 / tick
    self._slash_proc = "/proc"

  def _LinuxStateToTr181(self, linux_state):
    """Maps Linux process states to TR-181 process state names.

    Args:
      linux_state: One letter describing the state of the linux process,
      as described in proc(5). One of "RSDZTW"

    Returns: the tr-181 string describing the process state.

    Raises: None
    """
    mapping = {
        "R" : "Running",
        "S" : "Sleeping",
        "D" : "Uninterruptible",
        "Z" : "Zombie",
        "T" : "Stopped",
        "W" : "Uninterruptible"}
    return mapping.get(linux_state, "Sleeping")

  def _JiffiesToMsec(self, utime, stime):
    ticks = int(utime) + int(stime)
    msecs = ticks * self._msec_per_jiffy
    return str(msecs)

  def _RemoveParens(self, command):
    return command[1:-1]

  @property
  def CPUUsage(self):
      return 0   # TODO(apenwarr): figure out what this should do

  @property
  def ProcessNumberOfEntries(self):
      return len(list(self.ProcessList))

  @property
  def ProcessList(self):
    """Walks through /proc/<pid>/stat to return a list of all processes.

    Args: none

    Returns:
      a list of Process namedtuple objects
    """
    processes = {}
    for proc in glob.glob(self._slash_proc + "/[0123456789]*/stat"):
      try:
         fields = open(proc).read().split()
         p = self.Process(PID=fields[self._PID],
                          Command=self._RemoveParens(fields[self._COMM]),
                          Size=fields[self._RSS],
                          Priority=fields[self._PRIO],
                          CPUTime=self._JiffiesToMsec(fields[self._UTIME],
                                                      fields[self._STIME]),
                          State=self._LinuxStateToTr181(fields[self._STATE]))
         p.ValidateExports()
         processes[p.PID] = p
      except IOError:
        # This isn't an error. We have a list of files which existed the
        # moment the glob.glob was run. If a process exits before we get
        # around to reading it, its /proc files will go away.
        continue
      except KeyError:
        # TODO(dgentry) should LOG if exception is not IOError
        continue
    return processes


def main():
  dp = DeviceInfo()
  #print tr.core.DumpSchema(dp)
  print tr.core.Dump(dp)

if __name__ == '__main__':
  main()
