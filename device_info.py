#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.DeviceInfo object.

Handles the Device.DeviceInfo portion of TR-181, as described
by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import os
import tr.core
import tr.tr181_v2_2 as tr181

BASEDEVICE = tr181.Device_v2_2


#pylint: disable-msg=W0231
class DeviceInfo(BASEDEVICE.DeviceInfo):
  """Outputs fields to Device.DeviceInfo specific to the Google Uno platform.

  This object handles the manufacturer name, OUI, model, serial number,
  hardware and software versions, etc.
  """

  def __init__(self):
    BASEDEVICE.DeviceInfo.__init__(self)
    self.Manufacturer = 'Google'
    self.ManufacturerOUI = '00:1a:11:00:00:00'
    self.ModelName = 'Uno'
    self.Description = 'CPE device for Google Fiber network'
    self.SerialNumber = '00000000'
    self.HardwareVersion = '0'
    self.AdditionalHardwareVersion = '0'
    self.SoftwareVersion = '0'
    self.AdditionalSoftwareVersion = '0'
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
    self.NetworkProperties.MaxTCPWindowSize = 0,   # TODO(apenwarr): fill me
    self.NetworkProperties.TCPImplementation = ''  # TODO(apenwarr): fill me
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

  Tests can set proc_uptime to a file with fake data, instead of /proc/uptime.
  """

  def __init__(self, proc_uptime='/proc/uptime'):
    self._proc_uptime = proc_uptime

  def GetUptime(self):
    """Returns a string of the number of seconds since the system booted."""
    try:
      uptime = float(open(self._proc_uptime).read().split()[0])
    except IOError:
      # TODO(dgentry) - LOG the exception, but return zeros by default
      uptime = 0.0
    return str(int(uptime))


class MemoryStatusLinux26(BASEDEVICE.DeviceInfo.MemoryStatus):
  """Abstraction to get memory information from the underlying platform.

  Reads proc/meminfo to find TotalMem and FreeMem.

  Tests can set proc_meminfo to a file with fake data instead of /proc/meminfo
  """

  def __init__(self, proc_meminfo='/proc/meminfo'):
    BASEDEVICE.DeviceInfo.MemoryStatus.__init__(self)
    self._proc_meminfo = proc_meminfo
    (self._totalmem, self._freemem) = self._GetMemInfo(proc_meminfo)

  @property
  def Total(self):
    return self._totalmem

  @property
  def Free(self):
    return self._freemem

  def _GetMemInfo(self, proc_meminfo):
    """Fetch TotalMem and FreeMem from the underlying platform.

    Args:
      proc_meminfo - path to /proc/meminfo (tests can override with fake data)

    Returns:
      a list of two integers, (totalmem, freemem)
    """
    totalmem = 0
    freemem = 0
    try:
      pfile = open(proc_meminfo)
      for line in pfile:
        fields = line.split()
        name = fields[0]
        value = fields[1]
        if name == 'MemTotal:':
          totalmem = int(value)
        elif name == 'MemFree:':
          freemem = int(value)
    except IOError:
      # TODO(dgentry): LOG the exception, but return zeros by default
      pass
    return (totalmem, freemem)


class ProcessStatusLinux26(BASEDEVICE.DeviceInfo.ProcessStatus):
  """Get information about running processes on Linux 2.6.

  Reads /proc/<pid> to get information about processes.

  Tests can set slash_proc to a directory structure with fake data.
  """
  # Field ordering in /proc/<pid>/stat
  _PID = 0
  _COMM = 1
  _STATE = 2
  _UTIME = 13
  _STIME = 14
  _PRIO = 17
  _RSS = 23

  def __init__(self, slash_proc='/proc'):
    BASEDEVICE.DeviceInfo.ProcessStatus.__init__(self)
    tick = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    self._msec_per_jiffy = 1000 / tick
    self._slash_proc = slash_proc
    self.ProcessList = tr.core.AutoDict('ProcessList',
                                        iteritems=self.IterProcesses,
                                        getitem=self.GetProcess)

  def _LinuxStateToTr181(self, linux_state):
    """Maps Linux process states to TR-181 process state names.

    Args:
      linux_state: One letter describing the state of the linux process,
        as described in proc(5). One of "RSDZTW"

    Returns:
      the tr-181 string describing the process state.
    """
    mapping = {
        'R': 'Running',
        'S': 'Sleeping',
        'D': 'Uninterruptible',
        'Z': 'Zombie',
        'T': 'Stopped',
        'W': 'Uninterruptible'}
    return mapping.get(linux_state, 'Sleeping')

  def _JiffiesToMsec(self, utime, stime):
    ticks = int(utime) + int(stime)
    msecs = ticks * self._msec_per_jiffy
    return str(msecs)

  def _RemoveParens(self, command):
    return command[1:-1]

  def _ProcFileName(self, pid):
    return '%s/%s/stat' % (self._slash_proc, pid)

  @property
  def CPUUsage(self):
    return 0   # TODO(apenwarr): figure out what this should do

  @property
  def ProcessNumberOfEntries(self):
    return len(self.ProcessList)

  def GetProcess(self, pid):
    """Get a self.Process() object for the given pid."""
    try:
      f = open(self._ProcFileName(pid))
    except IOError:
      raise KeyError(pid)
    fields = f.read().split()
    p = self.Process(PID=fields[self._PID],
                     Command=self._RemoveParens(fields[self._COMM]),
                     Size=fields[self._RSS],
                     Priority=fields[self._PRIO],
                     CPUTime=self._JiffiesToMsec(fields[self._UTIME],
                                                 fields[self._STIME]),
                     State=self._LinuxStateToTr181(fields[self._STATE]))
    p.ValidateExports()
    return p

  def IterProcesses(self):
    """Walks through /proc/<pid>/stat to return a list of all processes."""
    for filename in glob.glob(self._ProcFileName('[0123456789]*')):
      pid = int(filename.split('/')[-2])
      try:
        proc = self.GetProcess(pid)
      except KeyError:
        # This isn't an error. We have a list of files which existed the
        # moment the glob.glob was run. If a process exits before we get
        # around to reading it, its /proc files will go away.
        continue
      yield pid, proc


def main():
  dp = DeviceInfo()
  #print tr.core.DumpSchema(dp)
  print tr.core.Dump(dp)

if __name__ == '__main__':
  main()
