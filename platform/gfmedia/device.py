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
# pylint: disable-msg=C6409

"""tr-181 Device implementations for supported platforms."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fcntl
import glob
import os
import subprocess
import traceback

import google3

import dm.binwifi
import dm.brcmmoca
import dm.brcmmoca2
import dm.brcmwifi
import dm.device_info
import dm.dns
import dm.dnsmasq
import dm.ethernet
import dm.host
import dm.igd_time
import dm.inadyn
import dm.ipinterface
import dm.miniupnp
import dm.nat
import dm.periodic_statistics
import dm.storage
import dm.temperature
import dm.traceroute
import platform_config
import pynetlinux
import tornado.ioloop
import tr.core
import tr.download
import tr.session
import tr.tr098_v1_2
import tr.tr181_v2_6 as tr181
import tr.x_catawampus_tr181_2_0

import gfibertv
import gvsb
import hat
import isostream
import ookla
import ssh
import stbservice

QCASWITCHPORT = None
try:
  import qca83xx
  if qca83xx.IsQCA8337():
    import dm.qca83xx_ethernet
    QCASWITCHPORT = dm.qca83xx_ethernet.EthernetInterfaceQca83xx
except ImportError:
  # Not an error, several platforms don't compile in qca83xx.
  pass
except qca83xx.SdkError:
  traceback.print_exc()
  print 'Continuing catawampus startup'

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
CATA181 = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
PYNETIFCONF = pynetlinux.ifconfig.Interface

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
CONFIGDIR = '/config/tr69'
GINSTALL = 'ginstall.py'
HNVRAM = 'hnvram'
ISNETWORKBOX = 'is-network-box'
LEDSTATUS = '/tmp/gpio/ledstate'
NAND_MB = '/proc/sys/dev/repartition/nand_size_mb'
PROC_CPUINFO = '/proc/cpuinfo'
REBOOT = 'tr69_reboot'
REPOMANIFEST = '/etc/manifest'
VERSIONFILE = '/etc/version'


def _ExistingInterfaces(ifcnames):
  out = []
  for ifcname in ifcnames:
    try:
      PYNETIFCONF(ifcname).get_index()
      out.append(ifcname)
    except IOError:
      pass
  return out


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFMedia devices."""

  def __init__(self, ioloop=None):
    super(PlatformConfig, self).__init__()

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    if os.path.isdir('/var/media/swimage'):
      return '/var/media/swimage'
    elif os.path.isdir('/user/swimage'):
      return '/user/swimage'
    elif os.path.isdir('/tmp/swimage'):
      return '/tmp/swimage'
    else:
      return '/tmp'


class DeviceId(dm.device_info.DeviceIdMeta):
  """Fetch the DeviceInfo parameters from NVRAM."""

  AdditionalHardwareVersion = tr.types.ReadOnlyString('')
  AdditionalSoftwareVersion = tr.types.ReadOnlyString('')
  Description = tr.types.ReadOnlyString('Set top box for Google Fiber network')
  HardwareVersion = tr.types.ReadOnlyString('')
  Manufacturer = tr.types.ReadOnlyString('Google Fiber')
  ManufacturerOUI = tr.types.ReadOnlyString('F88FCA')
  ModelName = tr.types.ReadOnlyString('')
  ModemFirmwareVersion = tr.types.ReadOnlyString('0')
  ProductClass = tr.types.ReadOnlyString('0')
  SerialNumber = tr.types.ReadOnlyString('')
  SoftwareVersion = tr.types.ReadOnlyString('')

  def __init__(self):
    super(DeviceId, self).__init__()
    addlhwvers = self._GetNvramParam('GPN', default='')
    type(self).AdditionalHardwareVersion.Set(self, addlhwvers)
    addlswvers = self._GetOneLine(REPOMANIFEST, '')
    type(self).AdditionalSoftwareVersion.Set(self, addlswvers)
    type(self).HardwareVersion.Set(self, self._HardwareVersion())
    modelname = self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')
    type(self).ModelName.Set(self, modelname)
    product_class = self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')
    type(self).ProductClass.Set(self, product_class)
    type(self).SerialNumber.Set(self, self._SerialNumber())
    swvers = self._GetOneLine(VERSIONFILE, '0')
    type(self).SoftwareVersion.Set(self, swvers)

  def _GetOneLine(self, filename, default):
    try:
      with open(filename, 'r') as f:
        return f.readline().strip()
    except IOError:
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
    if len(outlist) > 1 and outlist[1].strip():
      return outlist[1].strip()
    else:
      return default

  def _SerialNumber(self):
    serial = self._GetNvramParam('1ST_SERIAL_NUMBER', default=None)
    if serial is None:
      serial = self._GetNvramParam('SERIAL_NO', default='000000000000')
    return serial

  def _HardwareVersion(self):
    """Return NVRAM HW_REV, inferring one if not present."""
    hw_rev = self._GetNvramParam('HW_REV', default=None)
    if hw_rev:
      return hw_rev

    # initial builds with no HW_REV; infer a rev.
    cpu = open(PROC_CPUINFO, 'r').read()
    if cpu.find('BCM7425B2') > 0:
      # B2 chip with 4 Gig MLC flash == rev1. 1 Gig SLC flash == rev2.
      try:
        siz = int(open(NAND_MB, 'r').read())
      except OSError:
        return '?'
      if siz == 4096:
        return '1'
      if siz == 1024:
        return '2'
    return '0'


class Installer(tr.download.Installer):
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

  def on_stdout(self, fd, unused_events):
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


class Services(tr181.Device_v2_6.Device.Services):
  """Implements tr-181 Device.Services."""

  def __init__(self):
    super(Services, self).__init__()
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
          num += 1
      except OSError:
        pass

    num = 0
    for i in range(32):
      ubiname = 'ubi' + str(i)
      try:
        if os.stat('/sys/class/ubi/' + ubiname):
          ubi = dm.storage.FlashMediumUbiLinux26(ubiname)
          self.StorageServices.X_CATAWAMPUS_ORG_FlashMediaList[str(num)] = ubi
          num += 1
      except OSError:
        pass


class Ethernet(tr181.Device_v2_6.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for GFMedia platforms."""

  InterfaceNumberOfEntries = tr.types.NumberOf('InterfaceList')
  LinkNumberOfEntries = tr.types.NumberOf('LinkList')
  RMONStatsNumberOfEntries = tr.types.NumberOf('RMONStatsList')
  VLANTerminationNumberOfEntries = tr.types.NumberOf('VLANTerminationList')

  def __init__(self):
    super(Ethernet, self).__init__()
    self.InterfaceList = {}
    self.LinkList = {}
    self.RMONStatsList = {}
    self.VLANTerminationList = {}

    i = 1
    for ifc in _ExistingInterfaces(['eth0', 'wan0', 'wan0.2']):
      qprefix = '/sys/kernel/debug/bcmgenet/%s/bcmgenet_discard_cnt_q' % ifc
      qglob = glob.glob(qprefix + '*')
      self.InterfaceList[str(i)] = dm.ethernet.EthernetInterfaceLinux26(
          ifname=ifc,
          qfiles=(qprefix + '%d') if qglob else None,
          numq=len(qglob),
          hipriq=1 if qglob else 0)
      i += 1
    if QCASWITCHPORT is not None:
      mac = PYNETIFCONF('lan0').get_mac()
      for port in range(1, 5):
        q = QCASWITCHPORT(portnum=port, mac=mac, ifname='lan0')
        self.InterfaceList[str(i)] = q
        i += 1
    i = 256
    for ifc in _ExistingInterfaces(['br0', 'lan0']):
      e = dm.ethernet.EthernetInterfaceLinux26(ifname=ifc)
      self.InterfaceList[str(i)] = e
      i -= 1


class Moca(tr181.Device_v2_6.Device.MoCA):
  """Implementation of tr-181 Device.MoCA for GFMedia platforms."""

  def __init__(self):
    super(Moca, self).__init__()
    ifname = _ExistingInterfaces(['moca0', 'eth1'])[0]
    qfiles = '/sys/kernel/debug/bcmgenet/%s/bcmgenet_discard_cnt_q%%d' % ifname
    numq = 17
    hipriq = 1
    self.InterfaceList = {}
    if dm.brcmmoca2.IsMoca2_0():
      self.InterfaceList['1'] = dm.brcmmoca2.BrcmMocaInterface(
          ifname=ifname, qfiles=qfiles, numq=numq, hipriq=hipriq)
    elif dm.brcmmoca.IsMoca1_1():
      self.InterfaceList['1'] = dm.brcmmoca.BrcmMocaInterface(
          ifname=ifname, qfiles=qfiles, numq=numq, hipriq=hipriq)

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


class FanReadGpio(CATA181.DeviceInfo.TemperatureStatus.X_CATAWAMPUS_ORG_Fan):
  """Implementation of Fan object, reading rev/sec from a file."""
  Name = tr.types.ReadOnlyString('')

  def __init__(self, name='Fan', speed_filename='/tmp/gpio/fanspeed',
               percent_filename='/tmp/gpio/fanpercent'):
    super(FanReadGpio, self).__init__()
    type(self).Name.Set(self, name)
    self.Unexport(params=['DesiredRPM'])
    self._speed_filename = speed_filename
    self._percent_filename = percent_filename

  @property
  def RPM(self):
    try:
      f = open(self._speed_filename, 'r')
    except IOError as e:
      print 'Fan speed file %r: %s' % (self._speed_filename, e)
      return -1
    try:
      rps2 = int(f.read())
      return rps2 * 30
    except ValueError as e:
      print 'FanReadGpio RPM %r: %s' % (self._speed_filename, e)
      return -1

  @property
  def DesiredPercentage(self):
    try:
      f = open(self._percent_filename, 'r')
    except IOError as e:
      print 'Fan percent file %r: %s' % (self._percent_filename, e)
      return -1
    try:
      return int(f.read())
    except ValueError as e:
      print 'FanReadGpio DesiredPercentage %r: %s' % (self._percent_filename, e)
      return -1


class IP(tr181.Device_v2_6.Device.IP):
  """tr-181 Device.IP implementation for Google Fiber media platforms."""
  # Enable fields are supposed to be writeable, but we don't support that.
  IPv4Capable = tr.types.ReadOnlyBool(True)
  IPv4Enable = tr.types.ReadOnlyBool(True)
  IPv4Status = tr.types.ReadOnlyString('Enabled')
  IPv6Capable = tr.types.ReadOnlyBool(True)
  IPv6Enable = tr.types.ReadOnlyBool(True)
  IPv6Status = tr.types.ReadOnlyString('Enabled')

  def __init__(self):
    super(IP, self).__init__()
    self.Unexport(['ULAPrefix'])
    self.InterfaceList = {}
    if _ExistingInterfaces(['br0']):
      self.InterfaceList[256] = dm.ipinterface.IPInterfaceLinux26(
          ifname='br0', lowerlayers='Device.Ethernet.Interface.256')

    # Maintain numbering consistency between GFHD100 and GFRG200.
    # The LAN interface is first, then the MoCA interface, then the WAN
    # interfaces (if any) and then wifi (if any).
    lanifc = _ExistingInterfaces(['lan0', 'eth0'])
    if lanifc:
      self.InterfaceList[1] = dm.ipinterface.IPInterfaceLinux26(
          ifname=lanifc[0], lowerlayers='Device.Ethernet.Interface.1')
    mocaifc = _ExistingInterfaces(['moca0', 'eth1'])
    if mocaifc:
      self.InterfaceList[2] = dm.ipinterface.IPInterfaceLinux26(
          ifname=mocaifc[0], lowerlayers='Device.MoCA.Interface.1')

    if _ExistingInterfaces(['wan0']):
      self.InterfaceList[4] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wan0', lowerlayers='Device.Ethernet.Interface.1')
    if _ExistingInterfaces(['wan0.2']):
      self.InterfaceList[5] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wan0.2', lowerlayers='Device.Ethernet.Interface.2')

    if _ExistingInterfaces(['wlan0']):
      self.InterfaceList[6] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan0', lowerlayers='')
    if _ExistingInterfaces(['wlan1']):
      self.InterfaceList[7] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan1', lowerlayers='')
    if _ExistingInterfaces(['eth2']):
      self.InterfaceList[8] = dm.ipinterface.IPInterfaceLinux26(
          ifname='eth2', lowerlayers='')

    self.ActivePortList = {}
    self.Diagnostics = IPDiagnostics()

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def ActivePortNumberOfEntries(self):
    return len(self.ActivePortList)


class IPDiagnostics(CATA181.Device.IP.Diagnostics):
  """tr-181 Device.IP.Diagnostics for Google Fiber media platforms."""

  def __init__(self):
    super(IPDiagnostics, self).__init__()
    self.Unexport(objects=['IPPing'])
    self.TraceRoute = dm.traceroute.TraceRoute()
    self.X_CATAWAMPUS_ORG_Speedtest = ookla.Speedtest()
    self.X_CATAWAMPUS_ORG_Isostream = isostream.Isostream()


class Device(tr181.Device_v2_6.Device):
  """tr-181 Device implementation for Google Fiber media platforms."""

  RootDataModelVersion = tr.types.ReadOnlyString('2.6')

  def __init__(self, device_id, periodic_stats, dmroot):
    super(Device, self).__init__()
    self._UnexportStuff()
    # TODO(dgentry): figure out why these are not being exported automatically.
    self.Export(objects=['DeviceInfo', 'NAT', 'X_CATAWAMPUS-ORG_DynamicDNS', 'UPnP'])
    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    led = dm.device_info.LedStatusReadFromFile('LED', LEDSTATUS)
    self.DeviceInfo.AddLedStatus(led)
    self.DHCPv4 = dm.dnsmasq.DHCPv4()
    self.DNS = dm.dns.DNS()
    self.Ethernet = Ethernet()
    self.IP = IP()
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.MoCA = Moca()
    self.NAT = dm.nat.NAT(dmroot=dmroot)
    self.Services = Services()
    self.InterfaceStackList = {}
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats
    self.UPnP = dm.miniupnp.UPnP()
    self.X_CATAWAMPUS_ORG_DynamicDNS = dm.inadyn.Inadyn()
    self._AddTemperatureStuff()
    self._AddHostsStuff(dmroot=dmroot)

  @property
  def InterfaceStackNumberOfEntries(self):
    return len(self.InterfaceStackList)

  def _UnexportStuff(self):
    self.Unexport(objects=[
        'ATM', 'Bridging', 'CaptivePortal', 'DHCPv6', 'DSL', 'DSLite',
        'ETSIM2M', 'Firewall', 'GatewayInfo', 'Ghn', 'HPNA',
        'HomePlug', 'IEEE8021x', 'IPsec', 'IPv6rd', 'LANConfigSecurity',
        'NAT', 'NeighborDiscovery', 'Optical', 'PPP', 'PTM', 'QoS',
        'RouterAdvertisement', 'Routing', 'SmartCardReaders',
        'UPA', 'USB', 'Users', 'WiFi'])

  def _AddTemperatureStuff(self):
    # GFHD100 & GFMS100 both monitor CPU temperature.
    # GFMS100 also monitors hard drive temperature.
    ts = self.DeviceInfo.TemperatureStatus
    ts.AddFan(FanReadGpio())
    ts.AddSensor(name='CPU temperature',
                 sensor=dm.temperature.SensorReadFromFile(
                     '/tmp/gpio/cpu_temperature'))
    for drive in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
      try:
        if os.stat('/sys/block/' + drive):
          ts.AddSensor(name='Hard drive temperature ' + drive,
                       sensor=dm.temperature.SensorHdparm(drive))
      except OSError:
        pass

  def _AddHostsStuff(self, dmroot):
    """Add tr-181 Device.Host implementation.

    Args:
      dmroot: the device model root object.
    """
    # this is just a lookup table. It is harmless to have extra interfaces,
    # like Wifi interfaces on GFMS100 (which has no wifi).
    iflookup = {
        'eth1.0': 'Device.MoCA.Interface.1',
        'moca0.0': 'Device.MoCA.Interface.1',
    }
    self.Hosts = dm.host.Hosts(iflookup=iflookup, bridgename='br0', dmroot=dmroot)


class LANDevice(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice for Google Fiber media platforms."""

  LANWLANConfigurationNumberOfEntries = tr.types.NumberOf(
      'WLANConfigurationList')
  LANEthernetInterfaceNumberOfEntries = tr.types.NumberOf(
      'LANEthernetInterfaceConfigList')
  LANUSBInterfaceNumberOfEntries = tr.types.NumberOf(
      'LANUSBInterfaceConfigList')

  def __init__(self):
    super(LANDevice, self).__init__()
    self.Unexport(['Alias'])
    self.Unexport(objects=['Hosts', 'LANHostConfigManagement'])
    self.LANEthernetInterfaceConfigList = {}
    self.LANUSBInterfaceConfigList = {}
    self.WLANConfigurationList = {}
    i = 1
    for wifc in _ExistingInterfaces(['eth2']):
      wifi = dm.brcmwifi.BrcmWifiWlanConfiguration(wifc)
      self.WLANConfigurationList[str(i)] = wifi
      i += 1
    bands = {'wlan0': '2.4', 'wlan1': '5'}
    for wifc in _ExistingInterfaces(['wlan0', 'wlan1']):
      wifi = dm.binwifi.WlanConfiguration(wifc, band=bands[wifc])
      self.WLANConfigurationList[str(i)] = wifi
      i += 1


class InternetGatewayDevice(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.Unexport(params=['DeviceSummary'])
    self.Unexport(objects=['CaptivePortal', 'DeviceConfig',
                           'DownloadDiagnostics', 'IPPingDiagnostics',
                           'LANConfigSecurity', 'LANInterfaces',
                           'Layer2Bridging', 'Layer3Forwarding',
                           'QueueManagement', 'Services',
                           'TraceRouteDiagnostics', 'UploadDiagnostics',
                           'UserInterface'])
    self.Unexport(lists=['WANDevice'])
    self.LANDeviceList = {'1': LANDevice()}
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in

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


# pylint: disable-msg=unused-argument
def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = Installer
  params = []
  objects = []
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  device_model_root.Device = Device(dev_id, periodic_stats,
                                    dmroot=device_model_root)
  device_model_root.InternetGatewayDevice = InternetGatewayDevice(
      dev_id, periodic_stats)
  device_model_root.X_GOOGLE_COM_GVSB = gvsb.Gvsb()
  device_model_root.X_GOOGLE_COM_SSH = ssh.Ssh()
  tvrpc = gfibertv.GFiberTv(mailbox_url='http://localhost:51834/xmlrpc',
                            my_serial=dev_id.SerialNumber)
  device_model_root.X_GOOGLE_COM_GFIBERTV = tvrpc
  device_model_root.X_GOOGLE_COM_HAT = hat.Hat()
  objects.append('Device')
  objects.append('InternetGatewayDevice')
  objects.append('X_GOOGLE-COM_SSH')
  objects.append('X_GOOGLE-COM_GVSB')
  objects.append('X_GOOGLE-COM_GFIBERTV')
  objects.append('X_GOOGLE-COM_HAT')
  return (params, objects)


def main():
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  root = Device(dev_id, periodic_stats)
  root.ValidateExports()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
