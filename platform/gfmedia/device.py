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
# pylint:disable=invalid-name

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
import dm.captive_portal
import dm.device_info
import dm.dns
import dm.dnsmasq
import dm.ethernet
import dm.host
import dm.igd_time
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
import tr.handle
import tr.helpers
import tr.session
import tr.x_catawampus_tr098_1_0
import tr.x_catawampus_tr181_2_0
import stbservice

QCASWITCHPORT = None
try:
  import qca83xx  # pylint:disable=g-import-not-at-top
  if qca83xx.IsQCA8337():
    import dm.qca83xx_ethernet  # pylint:disable=g-import-not-at-top
    QCASWITCHPORT = dm.qca83xx_ethernet.EthernetInterfaceQca83xx
except ImportError:
  # Not an error, several platforms don't compile in qca83xx.
  pass
except qca83xx.SdkError:
  traceback.print_exc()
  print 'Continuing catawampus startup'

BASE98 = tr.x_catawampus_tr098_1_0.X_CATAWAMPUS_ORG_InternetGatewayDevice_v1_0
BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE181 = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
PYNETIFCONF = pynetlinux.ifconfig.Interface

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
ACTIVEWAN = 'activewan'
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


def _DoesInterfaceExist(ifcname):
  try:
    PYNETIFCONF(ifcname).get_index()
    return True
  except IOError:
    return False


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

  AdditionalHardwareVersion = tr.cwmptypes.ReadOnlyString('')
  AdditionalSoftwareVersion = tr.cwmptypes.ReadOnlyString('')
  Description = tr.cwmptypes.ReadOnlyString(
      'Set top box for Google Fiber network')
  HardwareVersion = tr.cwmptypes.ReadOnlyString('')
  Manufacturer = tr.cwmptypes.ReadOnlyString('Google Fiber')
  ManufacturerOUI = tr.cwmptypes.ReadOnlyString('F88FCA')
  ModelName = tr.cwmptypes.ReadOnlyString('')
  ModemFirmwareVersion = tr.cwmptypes.ReadOnlyString('0')
  ProductClass = tr.cwmptypes.ReadOnlyString('0')
  SerialNumber = tr.cwmptypes.ReadOnlyString('')
  SoftwareVersion = tr.cwmptypes.ReadOnlyString('')

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
    """Return NVRAM HW_VER, inferring one if not present."""
    hw_ver = self._GetNvramParam('HW_VER', default=None)
    if hw_ver:
      return hw_ver

    # initial builds with no HW_VER; infer a version.
    cpu = open(PROC_CPUINFO).read()
    if cpu.find('BCM7425B2') > 0:
      # B2 chip with 4 Gig MLC flash == rev1. 1 Gig SLC flash == rev2.
      try:
        siz = int(open(NAND_MB).read())
      except (OSError, IOError):
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

  def Install(self, file_type, target_filename, callback):
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

  def Reboot(self):
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


class Services(BASE181.Device.Services):
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


def activewan(ifname):
  """Returns 'Down' if ifname is not the active WAN port."""
  out = tr.helpers.Activewan(ACTIVEWAN)
  if not out or out == ifname:
    return ''
  return 'Down'


class Ethernet(BASE181.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for GFMedia platforms."""

  InterfaceNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceList')
  LinkNumberOfEntries = tr.cwmptypes.NumberOf('LinkList')
  RMONStatsNumberOfEntries = tr.cwmptypes.NumberOf('RMONStatsList')
  VLANTerminationNumberOfEntries = tr.cwmptypes.NumberOf('VLANTerminationList')

  def __init__(self):
    super(Ethernet, self).__init__()
    self.InterfaceList = {}
    self.LinkList = {}
    self.RMONStatsList = {}
    self.VLANTerminationList = {}

    has_wan_port = False
    if _DoesInterfaceExist('eth0'):
      qprefix = '/sys/kernel/debug/bcmgenet/eth0/bcmgenet_discard_cnt_q'
      qglob = glob.glob(qprefix + '*')
      self.InterfaceList[1] = dm.ethernet.EthernetInterfaceLinux26(
          ifname='eth0',
          qfiles=(qprefix + '%d') if qglob else None,
          numq=len(qglob),
          hipriq=1 if qglob else 0)
    elif _DoesInterfaceExist('wan0'):
      has_wan_port = True
      self.InterfaceList[1] = dm.ethernet.EthernetInterfaceLinux26(
          ifname='wan0', qfiles=None, numq=0, hipriq=0,
          status_fcn=lambda: activewan('wan0'))

    if _DoesInterfaceExist('wan0.2'):
      has_wan_port = True
      self.InterfaceList[2] = dm.ethernet.EthernetInterfaceLinux26(
          ifname='wan0.2', qfiles=None, numq=0, hipriq=0,
          status_fcn=lambda: activewan('wan0.2'))

    if QCASWITCHPORT is not None:
      mac = PYNETIFCONF('lan0').get_mac()
      for port in range(1, 5):
        q = QCASWITCHPORT(portnum=port, mac=mac, ifname='lan0')
        self.InterfaceList[2 + port] = q

    if _DoesInterfaceExist('br0'):
      e = dm.ethernet.EthernetInterfaceLinux26(ifname='br0')
      if has_wan_port:
        # though all platforms have a br0 interface, it is used
        # very differently on Network Boxes versus not. On
        # Network Box it is the LAN port, and ACS should assign
        # an internal address to it. On non-Network Box, it is
        # the uplink. We give them different numbers to avoid
        # accidentally mistaking one use for the other.
        self.InterfaceList[254] = e
        # For a transition period, support both 254 and 256
        self.InterfaceList[256] = e
      else:
        self.InterfaceList[256] = e

    if _DoesInterfaceExist('lan0'):
      e = dm.ethernet.EthernetInterfaceLinux26(ifname='lan0')
      self.InterfaceList[255] = e

    # Do not use idx 254, it is used for br0 above if has_wan_port


class Moca(BASE181.Device.MoCA):
  """Implementation of tr-181 Device.MoCA for GFMedia platforms."""

  def __init__(self):
    super(Moca, self).__init__()
    ifname = 'moca0' if _DoesInterfaceExist('moca0') else 'eth1'
    if os.path.exists('/sys/kernel/debug/bcmgenet'):
      qfiles = (
          '/sys/kernel/debug/bcmgenet/%s/bcmgenet_discard_cnt_q%%d' % ifname)
      numq = 17
      hipriq = 1
    else:
      qfiles = None
      numq = hipriq = 0
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


class FanReadGpio(
    BASE181.Device.DeviceInfo.TemperatureStatus.X_CATAWAMPUS_ORG_Fan):
  """Implementation of Fan object, reading rev/sec from a file."""
  Name = tr.cwmptypes.ReadOnlyString('')

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


class IP(BASE181.Device.IP):
  """tr-181 Device.IP implementation for Google Fiber media platforms."""
  # Enable fields are supposed to be writeable, but we don't support that.
  IPv4Capable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv4Status = tr.cwmptypes.ReadOnlyString('Enabled')
  IPv6Capable = tr.cwmptypes.ReadOnlyBool(True)
  IPv6Enable = tr.cwmptypes.ReadOnlyBool(True)
  IPv6Status = tr.cwmptypes.ReadOnlyString('Enabled')

  def __init__(self):
    super(IP, self).__init__()
    self.Unexport(['ULAPrefix'])
    self.InterfaceList = {}
    if _DoesInterfaceExist('br0'):
      self.InterfaceList[256] = dm.ipinterface.IPInterfaceLinux26(
          ifname='br0', lowerlayers='Device.Ethernet.Interface.256')

    # Maintain numbering consistency between GFHD100 and GFRG200.
    # The LAN interface is first, then the MoCA interface, then the WAN
    # interfaces (if any) and then wifi (if any).
    if _DoesInterfaceExist('lan0'):
      self.InterfaceList[1] = dm.ipinterface.IPInterfaceLinux26(
          ifname='lan0', lowerlayers='Device.Ethernet.Interface.255')
    elif _DoesInterfaceExist('eth0'):
      self.InterfaceList[1] = dm.ipinterface.IPInterfaceLinux26(
          ifname='eth0', lowerlayers='Device.Ethernet.Interface.1')

    if _DoesInterfaceExist('moca0'):
      self.InterfaceList[2] = dm.ipinterface.IPInterfaceLinux26(
          ifname='moca0', lowerlayers='Device.MoCA.Interface.1')
    elif _DoesInterfaceExist('eth1'):
      self.InterfaceList[2] = dm.ipinterface.IPInterfaceLinux26(
          ifname='eth1', lowerlayers='Device.MoCA.Interface.1')

    if _DoesInterfaceExist('wan0'):
      self.InterfaceList[4] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wan0', lowerlayers='Device.Ethernet.Interface.1')
    if _DoesInterfaceExist('wan0.2'):
      self.InterfaceList[5] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wan0.2', lowerlayers='Device.Ethernet.Interface.2')

    if _DoesInterfaceExist('wlan0'):
      self.InterfaceList[6] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan0', lowerlayers='')
    if _DoesInterfaceExist('wlan1'):
      self.InterfaceList[7] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan1', lowerlayers='')
    if _DoesInterfaceExist('eth2'):
      self.InterfaceList[8] = dm.ipinterface.IPInterfaceLinux26(
          ifname='eth2', lowerlayers='')
    if _DoesInterfaceExist('wlan0_portal'):
      self.InterfaceList[9] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan0_portal', lowerlayers='')
    if _DoesInterfaceExist('wlan1_portal'):
      self.InterfaceList[10] = dm.ipinterface.IPInterfaceLinux26(
          ifname='wlan1_portal', lowerlayers='')

    self.ActivePortList = {}
    self.Diagnostics = IPDiagnostics()

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def ActivePortNumberOfEntries(self):
    return len(self.ActivePortList)


class IPDiagnostics(BASE181.Device.IP.Diagnostics):
  """tr-181 Device.IP.Diagnostics for Google Fiber media platforms."""

  def __init__(self):
    super(IPDiagnostics, self).__init__()
    self.Unexport(objects=['IPPing', 'UploadDiagnostics',
                           'UDPEchoConfig', 'DownloadDiagnostics'])
    self.TraceRoute = dm.traceroute.TraceRoute()


class Device(BASE181.Device):
  """tr-181 Device implementation for Google Fiber media platforms."""

  RootDataModelVersion = tr.cwmptypes.ReadOnlyString('2.6')
  InterfaceStackNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceStackList')

  def __init__(self, device_id, periodic_stats, dmroot):
    super(Device, self).__init__()
    self.Unexport(objects=[
        'ATM', 'Bridging', 'BulkData',
        'DHCPv6', 'DLNA', 'DSL', 'DSLite', 'FaultMgmt',
        'ETSIM2M', 'FAP', 'Firewall', 'GatewayInfo', 'Ghn', 'HPNA',
        'HomePlug', 'IEEE8021x', 'IPsec', 'IPv6rd', 'LANConfigSecurity',
        'NeighborDiscovery', 'Optical', 'PPP', 'PTM', 'QoS',
        'RouterAdvertisement', 'Routing', 'Security',
        'SelfTestDiagnostics', 'SoftwareModules',
        'SmartCardReaders', 'Time',
        'UPA', 'USB', 'UserInterface', 'Users', 'WiFi'])
    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    led = dm.device_info.LedStatusReadFromFile('LED', LEDSTATUS)
    self.DeviceInfo.AddLedStatus(led)
    self.DHCPv4 = dm.dnsmasq.DHCPv4(dmroot=dmroot)
    self.DNS = dm.dns.DNS()
    self.Ethernet = Ethernet()
    self.IP = IP()
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.MoCA = Moca()
    self.NAT = dm.nat.NAT(dmroot=dmroot)
    self.Services = Services()
    self.InterfaceStackList = {}
    self.PeriodicStatistics = periodic_stats
    self.UPnP = dm.miniupnp.UPnP()
    self.CaptivePortal = dm.captive_portal.CaptivePortal()

    # Add platform temperature sensors.
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

    # Add platform host entries.
    # this is just a lookup table. It is harmless to have extra interfaces,
    # like Wifi interfaces on GFMS100 (which has no wifi).
    iflookup = {
        'eth1.0': 'Device.MoCA.Interface.1',
        'moca0.0': 'Device.MoCA.Interface.1',
    }
    self.Hosts = dm.host.Hosts(
        iflookup=iflookup, bridgename='br0', dmroot=tr.handle.Handle(dmroot))


class LANDevice(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice for Google Fiber media platforms."""

  LANWLANConfigurationNumberOfEntries = tr.cwmptypes.NumberOf(
      'WLANConfigurationList')
  LANEthernetInterfaceNumberOfEntries = tr.cwmptypes.NumberOf(
      'LANEthernetInterfaceConfigList')
  LANUSBInterfaceNumberOfEntries = tr.cwmptypes.NumberOf(
      'LANUSBInterfaceConfigList')

  def __init__(self, if_suffix, bridge):
    super(LANDevice, self).__init__()
    self.Unexport(['Alias'])
    self.Unexport(objects=['Hosts', 'LANHostConfigManagement'])
    self.LANEthernetInterfaceConfigList = {}
    self.LANUSBInterfaceConfigList = {}
    self.WLANConfigurationList = {}
    if _DoesInterfaceExist('eth2' + if_suffix):
      wifi = dm.brcmwifi.BrcmWifiWlanConfiguration('eth2' + if_suffix)
      self.WLANConfigurationList['1'] = wifi

    if (_DoesInterfaceExist('wlan0' + if_suffix)
        and _DoesInterfaceExist('wlan1' + if_suffix)):
      # Two radios, instantiate both with fixed bands
      wifi = dm.binwifi.WlanConfiguration('wlan0', if_suffix, bridge, '2.4')
      self.WLANConfigurationList['1'] = wifi
      wifi = dm.binwifi.WlanConfiguration('wlan1', if_suffix, bridge, '5',
                                          standard='ac', width_5g=80,
                                          autochan='HIGH')
      self.WLANConfigurationList['2'] = wifi
    elif _DoesInterfaceExist('wlan0' + if_suffix):
      # One radio, allow switching bands
      wifi = dm.binwifi.WlanConfiguration('wlan0', if_suffix, 'br0',
                                          width_5g=40, autochan='LOW')
      self.WLANConfigurationList['1'] = wifi


class InternetGatewayDevice(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice (deprecated but heavily used)."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.Unexport(params=['DeviceSummary', 'UserNumberOfEntries',
                          'SmartCardReaderNumberOfEntries'],
                  objects=['Capabilities', 'CaptivePortal', 'DeviceConfig',
                           'DLNA', 'DownloadAvailability',
                           'DownloadDiagnostics', 'FAP', 'FaultMgmt',
                           'Firewall',
                           'IPPingDiagnostics',
                           'LANConfigSecurity', 'LANInterfaces',
                           'Layer2Bridging', 'Layer3Forwarding',
                           'NSLookupDiagnostics',
                           'SelfTestDiagnostics',
                           'QueueManagement', 'Security', 'Services',
                           'SoftwareModules',
                           'TraceRouteDiagnostics',
                           'UDPEchoConfig', 'UploadDiagnostics',
                           'UPnP', 'USBHosts',
                           'UserInterface'],
                  lists=['WANDevice', 'SmartCardReader', 'User'])
    self.LANDeviceList = {'1': LANDevice('', 'br0'),
                          '2': LANDevice('_portal', '')}
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


# pylint:disable=unused-argument
def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  root = device_model_root
  tr.download.INSTALLER = Installer
  params = []
  objects = []
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  root.Device = Device(dev_id, periodic_stats, dmroot=root)
  root.InternetGatewayDevice = InternetGatewayDevice(dev_id, periodic_stats)
  objects.append('Device')
  objects.append('InternetGatewayDevice')

  return (params, objects)
