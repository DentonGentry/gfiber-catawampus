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
import xmlwitch

# Used for Device.DeviceInfo.ProcessStatus.Process.{i}
Process = collections.namedtuple('Process', ['PID', 'Command', 'Size',
                                             'Priority', 'CPUTime', 'State'])

class DeviceInfo(object):
  """Outputs TR-181 Device.DeviceInfo nodes.

  DeviceInfo is a composed object of four other platform specific
  objects. It retrieves data about the platform and formats it according to
  TR-181.

  Constructor args:
    device_info_platform: must provide a ToXml method
    uptime: must provide a GetUptime method
    memory_info: must provide a GetMemoryInfo method
    process_status: must provide a GetProcessStatus method
  """
  def __init__(self, device_info_platform, uptime, memory_info, process_status):
    self._device_info_platform = device_info_platform
    self._uptime = uptime
    self._memory_info = memory_info
    self._process_status = process_status

  def _MemoryInfoToXml(self, xml):
    """Outputs memory information to Device.DeviceInfo.MemoryStatus.

    The memory_info object implements an abstraction to get memory data
    from the underlying platform. It deliberately does not contain any
    TR-181 specifics, so we can more easily swap it out with a mock.
    This function performs the TR-181 formatting.

    Args:
      xml: The xmlwitch XML object for Device.DeviceInfo.

    Returns:
      The xmlwitch object after adding MemoryStatus.

    Raises: None
    """
    (totalmem, freemem) = self._memory_info.GetMemInfo()
    with xml.MemoryStatus:
      xml.Total(totalmem)
      xml.Free(freemem)
    return xml

  def _ProcessStatusToXml(self, xml):
    """Outputs a process list to Device.DeviceInfo.ProcessStatus.Process.{i}.

    The process_status object implements an abstraction from the underlying
    platform. It deliberately does not contain any TR-181 specifics, so we
    can more easily swap it out with a mock. This function performs the
    TR-181 formatting.

    Args:
      xml: The xmlwitch XML object for Device.DeviceInfo.

    Raises: None
    """
    processes = self._process_status.GetProcesses()
    with xml.Process:
      for (num, proc) in enumerate(processes):
        # Create XML node <0>, <1>, etc.
        with xml.__getitem__(str(num)):
          xml.PID(proc.PID)
          xml.Command(proc.Command)
          xml.Size(proc.Size)
          xml.Priority(proc.Priority)
          xml.CPUTime(proc.CPUTime)
          xml.State(proc.State)

  def ToXml(self, xml):
    """Outputs Device.DeviceInfo.

    Calls and formats output from the device_info_platform,
    uptime, memory_info, and process_status objects.

    Args:
      xml: The xmlwitch XML object for Device.

    Returns: the xmlwitch object after adding fields.

    Raises: None
    """
    with xml.DeviceInfo:
      self._device_info_platform.ToXml(xml)
      xml.UpTime(self._uptime.GetUptime())
      self._MemoryInfoToXml(xml)
      self._ProcessStatusToXml(xml)
    return xml

class DeviceInfoUno(object):
  """Outputs fields to Device.DeviceInfo specific to the Google Uno platform.

  This object handles the manufacturer name, OUI, model, serial number,
  hardware and software versions, etc.
  """
  def __init__(self):
    self._manufacturer = "Google"
    self._manufacturer_oui = "00:1a:11:00:00:00"
    self._model_name = "Uno"
    self._description = "CPE device for Google Fiber network"
    self._serial_number = "00000000"
    self._hardware_version = "0"
    self._software_version = "0"

  def ToXml(self, xml):
    """Outputs Device.DeviceInfo fields specific to this platform.

    Args:
      xml: The xmlwitch XML object for Device.DeviceInfo.

    Raises: None
    """
    xml.Manufacturer(self._manufacturer)
    xml.ManufacturerOUI(self._manufacturer_oui)
    xml.ModelName(self._model_name)
    xml.Description(self._description)
    xml.SerialNumber(self._serial_number)
    xml.HardwareVersion(self._hardware_version)
    xml.SoftwareVersion(self._software_version)


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
      # TODO(Dgentry) - LOG the exception, but return zeros by default
      uptime = 0.0
    return str(int(uptime))


class MemoryInfoLinux26(object):
  """Abstraction to get memory information from the underlying platform.

  Reads proc/meminfo to find TotalMem and FreeMem.

  Tests can set _proc_meminfo to a file with fake data instead of /proc/meminfo
  """
  def __init__(self):
    self._proc_meminfo = "/proc/meminfo"

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


class ProcessStatusLinux26(object):
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

  def GetProcesses(self):
    """Walks through /proc/<pid>/stat to return a list of all processes.

    Args: none

    Returns:
      a list of Process namedtuple objects
    """
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
        # moment the glob.glob was run. If a process exits before we get
        # around to reading it, its /proc files will go away.
        continue
      except KeyError:
        # TODO(dgentry) should LOG if exception is not IOError
        continue
    return processes


def main():
  dp = DeviceInfoUno()
  ut = UptimeLinux26()
  mi = MemoryInfoLinux26()
  ps = ProcessStatusLinux26()
  di = DeviceInfo(dp, ut, mi, ps)
  xml = xmlwitch.Builder(encoding='utf-8')
  print di.ToXml(xml)

if __name__ == '__main__':
  main()
