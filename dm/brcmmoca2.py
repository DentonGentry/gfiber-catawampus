#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Implementation of tr-181 MoCA objects for Broadcom chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import subprocess
import pynetlinux
import tr.core
import tr.session
import tr.tr181_v2_2
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
CATA181MOCA = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.MoCA
MOCAP = 'mocap'
PYNETIFCONF = pynetlinux.ifconfig.Interface


# Regexps to parse mocap output
EUI_RE = re.compile(r'^eui\s*:\s*((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
MAC_RE = re.compile(r'^Node\s+\d+\s+((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
MHZ_RE = re.compile(r'^rf_channel\s*:\s*\d+ - (\d+) MHz')
TX_RE = re.compile(r'^tx_packets\s*:\s*(\d+)')
RX_RE = re.compile(r'^rx_packets\s*:\s*(\d+)')
E1_RE = re.compile(r'rx_cw_uncorrected\s*:\s*(\d+)')
E2_RE = re.compile(r'rx_no_sync\s*:\s*(\d+)')
RX_CRC_RE = re.compile(r'^rx_.*_crc_error\s*:\s*(\d+)')
RX_TIMEOUT_RE = re.compile(r'^rx_.*_timeout_error\s*:\s*(\d+)')
TX_POWER_RE = re.compile(r'^tx_power\s*:\s*(\d+[.]?\d*)\s+dBm')
RX_POWER_RE = re.compile(r'^rx_power\s*:\s*(-?\d+[.]?\d*)\s+dBm')
SNR_RE = re.compile(r'^avg_snr\s*:\s*(\d+[.]?\d*)')
NBAS_RE = re.compile(r'^nbas\s*:\s*(\d+)')
RATE_RE = re.compile(r'^phy_rate\s*:\s*(\d+)\s+Mbps')
BITL_RE = re.compile(r'^\d+\s+-\s+\d+\s*:\s+([0-9a-fA-F]+)')


def IsMoca2_0():
  """Check for existence of the MoCA 2.0 utilities."""
  cmd = [MOCAP, 'get', '--fw_version']
  try:
    rc = subprocess.call(cmd)
    return True if rc == 0 else False
  except OSError:
    return False


def IntOrZero(arg):
  try:
    return int(arg)
  except (ValueError, TypeError):
    return 0


def FloatOrZero(arg):
  try:
    return float(arg)
  except (ValueError, TypeError):
    return 0.0


def _RegToMoCA(regval):
  moca = {'16': '1.0', '17': '1.1', '32': '2.0', '33': '2.1'}
  return moca.get(regval, '0.0')


def _CombineBitloading(bitlines):
  """Combine bitloading information into one string.

  Args:
    bitlines: a list of lines with ranges:
    ['000 - 031:  000099aaaaaaaaaaaaaaaaaaaaaaaaaa',
     '032 - 063:  aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    ...
     '480 - 511:  aaaaaaaaaaaaaaaaaaaaaaaaaaa99000']

  Returns:
    one contiguous string, '000099aaaaa...aaaa99000'
  """

  bitloading = []
  for line in sorted(bitlines):
    (_, bits) = line.split(':')
    bitloading.append(bits.strip())
  return ''.join(bitloading)


class BrcmMocaInterface(BASE181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""
  # TODO(dgentry) Supposed to be read/write, but we don't handle disabling.
  Enable = tr.cwmptypes.ReadOnlyBool(True)
  Name = tr.cwmptypes.ReadOnlyString('')
  # In theory LowerLayers is writeable, but it is nonsensical to write to it.
  LowerLayers = tr.cwmptypes.ReadOnlyString('')

  MAX_NODES_MOCA1 = 8
  MAX_NODES_MOCA2 = 16
  MaxNodes = tr.cwmptypes.ReadOnlyInt(0)

  Upstream = tr.cwmptypes.ReadOnlyBool(False)

  def __init__(self, ifname, upstream=False, qfiles=None, numq=0, hipriq=0):
    BASE181MOCA.Interface.__init__(self)
    type(self).MaxNodes.Set(self, self.MAX_NODES_MOCA2)
    type(self).Name.Set(self, ifname)
    type(self).Upstream.Set(self, bool(upstream))
    self._pynet = PYNETIFCONF(ifname)
    self._qfiles = qfiles
    self._numq = numq
    self._hipriq = hipriq

    self.Unexport(['Alias', 'MaxBitRate', 'MaxIngressBW', 'MaxEgressBW',
                   'PrivacyEnabledSetting', 'FreqCapabilityMask',
                   'FreqCurrentMaskSetting', 'FreqCurrentMask', 'KeyPassphrase',
                   'TxPowerLimit', 'PowerCntlPhyTarget', 'BeaconPowerLimit',
                   'NetworkTabooMask', 'NodeTabooMask', 'TxBcastRate',
                   'TxBcastPowerReduction'])
    self.Unexport(objects=['QoS'])

  @property
  def Stats(self):
    return BrcmMocaInterfaceStatsLinux26(self.Name, self._qfiles,
                                         self._numq, self._hipriq)

  @tr.session.cache
  def _MocapGet(self, args):
    """Return output of mocap get --args."""
    cmd = [MOCAP, 'get'] + args
    mc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  def _MocapGetField(self, lines, field):
    """Look for one field in output from a command.

    ex: field='SwVersion' would return 5.6.789 from
    vendorId              : 999999999   HwVersion             : 0x12345678
    SwVersion             : 5.6.789     self MoCA Version     : 0x11

    Args:
      lines: lines of output to search
      field: the text string to look for.
    Returns:
      The value of the field, or None.
    """

    m_re = re.compile(field + r'\s*:\s+(\S+)')
    for line in lines:
      mr = m_re.search(line)
      if mr is not None:
        return mr.group(1)
    return None

  @property
  def Status(self):
    if not self._pynet.is_up():
      return 'Down'
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    if link_up:
      return 'Up'
    else:
      return 'Dormant'

  @property
  def LastChange(self):
    """Parse linkUpTime y:m:d:h:m:s, return seconds."""
    up = self._MocapGetField(self._MocapGet(['--drv_info']),
                             'link_uptime').split(':')
    secs = 0
    for t in up:
      # linkUpTime ex: '23h:41m:30s'
      num = IntOrZero(t[:-1])
      if t[-1] == 'y':
        secs += int(num * (365.25 * 24.0 * 60.0 * 60.0))
      elif t[-1] == 'w':
        secs += num * (7 * 24 * 60 * 60)
      elif t[-1] == 'd':
        secs += num * (24 * 60 * 60)
      elif t[-1] == 'h':
        secs += num * (60 * 60)
      elif t[-1] == 'm':
        secs += num * 60
      elif t[-1] == 's':
        secs += num
    return secs

  @property
  def MACAddress(self):
    print 'get MAC for %r' % self.Name
    return self._pynet.get_mac()

  @property
  def FirmwareVersion(self):
    lines = self._MocapGet(['--node_status'])
    major = self._MocapGetField(lines, 'moca_sw_version_major')
    minor = self._MocapGetField(lines, 'moca_sw_version_minor')
    rev = self._MocapGetField(lines, 'moca_sw_version_rev')
    if major and minor and rev:
      return '.'.join([str(major), str(minor), str(rev)])
    else:
      return '0'

  @property
  def HighestVersion(self):
    reg = self._MocapGetField(self._MocapGet(['--node_status']),
                              'self_moca_version')
    return _RegToMoCA(reg)

  @property
  def CurrentVersion(self):
    reg = self._MocapGetField(self._MocapGet(['--network_status']),
                              'network_moca_version')
    return _RegToMoCA(reg)

  @property
  def NetworkCoordinator(self):
    nodeid = self._MocapGetField(self._MocapGet(['--network_status']),
                                 'nc_node_id')
    return IntOrZero(nodeid)

  @property
  def PreferredNC(self):
    prefer = self._MocapGetField(self._MocapGet(['--preferred_nc']),
                                 'preferred_nc')
    return True if prefer == '1' else False

  @property
  def NodeID(self):
    nodeid = self._MocapGetField(self._MocapGet(['--network_status']),
                                 'node_id')
    return IntOrZero(nodeid)

  @property
  def BackupNC(self):
    bnc = self._MocapGetField(self._MocapGet(['--network_status']),
                              'backup_nc_id')
    return IntOrZero(bnc)

  @property
  def PrivacyEnabled(self):
    private = self._MocapGetField(self._MocapGet(['--privacy_en']),
                                  'privacy_en')
    return True if private == '1' else False

  @property
  def CurrentOperFreq(self):
    lines = self._MocapGet(['--interface_status'])
    for line in lines:
      mhz = MHZ_RE.search(line)
      if mhz is not None:
        return int(mhz.group(1)) * 1000000
    return 0

  @property
  def LastOperFreq(self):
    lof = self._MocapGetField(self._MocapGet(['--lof']), 'lof')
    return int(lof) * 1000000

  @property
  def QAM256Capable(self):
    qam = self._MocapGetField(self._MocapGet(['--node_status']),
                              'qam_256_support')
    return True if qam == '1' else False

  @property
  def PacketAggregationCapability(self):
    pkts = self._MocapGetField(self._MocapGet(['--max_pkt_aggr']),
                               'max_pkt_aggr')
    return IntOrZero(pkts)

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  def _MocaGetNodeIDs(self):
    """Return a list of active MoCA Node IDs."""
    nodes = list()
    for i in range(16):
      mc = subprocess.Popen([MOCAP, 'get', '--node_stats', 'index', str(i)],
                            stdout=subprocess.PIPE)
      out, _ = mc.communicate(None)
      for line in out.splitlines():
        mac = MAC_RE.search(line)
        if mac is not None and mac.group(1) != '00:00:00:00:00:00':
          nodes.append(i)
    return nodes

  @property
  @tr.session.cache
  def AssociatedDeviceList(self):
    mocanodes = self._MocaGetNodeIDs()
    result = {}
    for idx, nodeid in enumerate(mocanodes, start=1):
      result[str(idx)] = BrcmMocaAssociatedDevice(nodeid)
    return result


class BrcmMocaInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    CATA181MOCA.Interface.Stats):
  """tr181 Device.MoCA.Interface.Stats for Broadcom chipsets."""

  def __init__(self, ifname, qfiles=None, numq=0, hipriq=0):
    netdev.NetdevStatsLinux26.__init__(self, ifname, qfiles, numq, hipriq)
    CATA181MOCA.Interface.Stats.__init__(self)
    if not qfiles:
      self.Unexport(['X_CATAWAMPUS-ORG_DiscardFrameCnts',
                     'X_CATAWAMPUS-ORG_DiscardPacketsReceivedHipri'])


class BrcmMocaAssociatedDevice(CATA181MOCA.Interface.AssociatedDevice):
  """tr-181 Device.MoCA.Interface.AssociatedDevice for Broadcom chipsets."""
  Active = tr.cwmptypes.ReadOnlyBool(True)
  MACAddress = tr.cwmptypes.ReadOnlyString('')
  NodeID = tr.cwmptypes.ReadOnlyInt(-1)
  PHYRxRate = tr.cwmptypes.ReadOnlyInt(0)
  PHYTxRate = tr.cwmptypes.ReadOnlyInt(0)
  RxBcastPowerLevel = tr.cwmptypes.ReadOnlyInt(0)
  RxErroredAndMissedPackets = tr.cwmptypes.ReadOnlyInt(0)
  RxPackets = tr.cwmptypes.ReadOnlyInt(0)
  RxPowerLevel = tr.cwmptypes.ReadOnlyInt(0)
  RxSNR = tr.cwmptypes.ReadOnlyInt(0)
  TxBcastRate = tr.cwmptypes.ReadOnlyInt(0)
  TxPackets = tr.cwmptypes.ReadOnlyInt(0)
  X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxPowerLevel_dBm = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxSNR_dB = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_TxBitloading = tr.cwmptypes.ReadOnlyString('')
  X_CATAWAMPUS_ORG_RxBitloading = tr.cwmptypes.ReadOnlyString('')

  # mocap get --gen_node_ext_status <profile id>
  MOCAP_EXT_RX_UNICAST = 0
  MOCAP_EXT_RX_BROADCAST = 1
  MOCAP_EXT_RX_MAP = 2
  MOCAP_EXT_TX_UNICAST = 3
  MOCAP_EXT_TX_BROADCAST = 4
  MOCAP_EXT_TX_MAP = 5
  MOCAP_EXT_RX_UNICAST_VLPER = 6
  MOCAP_EXT_RX_UNICAST_NPER = 7
  MOCAP_EXT_RX_BROADCAST_VLPER = 8
  MOCAP_EXT_RX_BROADCAST_NPER = 9
  MOCAP_EXT_RX_MAP_2_0 = 10
  MOCAP_EXT_RX_OFDMA = 11
  MOCAP_EXT_TX_UNICAST_VLPER = 12
  MOCAP_EXT_TX_UNICAST_NPER = 13
  MOCAP_EXT_TX_BROADCAST_VLPER = 14
  MOCAP_EXT_TX_BROADCAST_NPER = 15
  MOCAP_EXT_TX_MAP_2_0 = 16
  MOCAP_EXT_TX_OFDMA = 17

  def __init__(self, nodeid):
    super(BrcmMocaAssociatedDevice, self).__init__()
    type(self).NodeID.Set(self, int(nodeid))
    self.Unexport(['HighestVersion', 'PacketAggregationCapability',
                   'PreferredNC', 'QAM256Capable', 'TxPowerControlReduction'])

    self._ParseNodeStats()
    self._ParseGenNodeExtStatus()

  @tr.session.cache
  def _ParseNodeStats(self):
    """Get stats for this node."""
    mc = subprocess.Popen([MOCAP, 'get', '--node_stats',
                           'index', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    rx_err = 0
    for line in out.splitlines():
      mac = MAC_RE.search(line)
      if mac is not None:
        type(self).MACAddress.Set(self, str(mac.group(1)))
      tx = TX_RE.search(line)
      if tx is not None:
        type(self).TxPackets.Set(self, IntOrZero(tx.group(1)))
      rx = RX_RE.search(line)
      if rx is not None:
        type(self).RxPackets.Set(self, IntOrZero(rx.group(1)))
      e1 = E1_RE.search(line)
      if e1 is not None:
        rx_err += IntOrZero(e1.group(1))
      e2 = E2_RE.search(line)
      if e2 is not None:
        rx_err += IntOrZero(e2.group(1))

    mc = subprocess.Popen([MOCAP, 'get', '--node_stats_ext',
                           'index', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    for line in out.splitlines():
      crc = RX_CRC_RE.search(line)
      if crc is not None:
        rx_err += IntOrZero(crc.group(1))
      timeout = RX_TIMEOUT_RE.search(line)
      if timeout is not None:
        rx_err += IntOrZero(timeout.group(1))

    type(self).RxErroredAndMissedPackets.Set(self, rx_err)

  @tr.session.cache
  def _ExtractGenNodeExtStatus(self, nodeid, profile):
    """Parse mocap get --gen_node_ext_status to return relevant information.

    Args:
      nodeid: integer nodeid, should be 0-15 for MoCA 2.0.
      profile: integer profile number. See MOCAP_EXT_* constants.

    Returns:
      a dictionary of extracted values.
    """
    rc = {'nbas': 0, 'phy_rate': 0,
          'rx_power': 0.0, 'tx_power': 0.0,
          'snr': 0.0, 'bitloading': ''}
    bitl = list()
    mc = subprocess.Popen([MOCAP, 'get', '--gen_node_ext_status', 'index',
                           str(nodeid), 'profile_type', str(profile)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    for line in out.splitlines():
      txp_re = TX_POWER_RE.search(line)
      if txp_re is not None:
        rc['tx_power'] = FloatOrZero(txp_re.group(1))
      rxp_re = RX_POWER_RE.search(line)
      if rxp_re is not None:
        rc['rx_power'] = FloatOrZero(rxp_re.group(1))
      snr_re = SNR_RE.search(line)
      if snr_re is not None:
        rc['snr'] = FloatOrZero(snr_re.group(1))
      nbas_re = NBAS_RE.search(line)
      if nbas_re is not None:
        rc['nbas'] = IntOrZero(nbas_re.group(1))
      rate_re = RATE_RE.search(line)
      if rate_re is not None:
        rc['phy_rate'] = IntOrZero(rate_re.group(1))
      bitl_re = BITL_RE.search(line)
      if bitl_re is not None:
        bitl.append(line)

    rc['bitloading'] = '$BRCM2$' + _CombineBitloading(bitl)
    return rc

  def _ParseGenNodeExtStatus(self):
    """Check TX and RX profiles of mocap --gen_node_ext_status."""
    rc = self._ExtractGenNodeExtStatus(self.NodeID,
                                       self.MOCAP_EXT_TX_UNICAST_VLPER)
    type(self).PHYTxRate.Set(self, rc['phy_rate'])
    type(self).X_CATAWAMPUS_ORG_TxBitloading.Set(self, rc['bitloading'])

    rc = self._ExtractGenNodeExtStatus(self.NodeID,
                                       self.MOCAP_EXT_RX_UNICAST_VLPER)
    type(self).PHYRxRate.Set(self, rc['phy_rate'])
    type(self).RxPowerLevel.Set(self, abs(int(rc['rx_power'])))
    type(self).RxSNR.Set(self, abs(int(rc['snr'])))
    type(self).X_CATAWAMPUS_ORG_RxBitloading.Set(self, rc['bitloading'])
    type(self).X_CATAWAMPUS_ORG_RxPowerLevel_dBm.Set(self, rc['rx_power'])
    type(self).X_CATAWAMPUS_ORG_RxSNR_dB.Set(self, rc['snr'])

    rc = self._ExtractGenNodeExtStatus(self.NodeID,
                                       self.MOCAP_EXT_TX_BROADCAST_VLPER)
    type(self).TxBcastRate.Set(self, rc['phy_rate'])

    rc = self._ExtractGenNodeExtStatus(self.NodeID,
                                       self.MOCAP_EXT_RX_BROADCAST_VLPER)
    type(self).RxBcastPowerLevel.Set(self, abs(int(rc['rx_power'])))
    type(self).X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm.Set(self, rc['rx_power'])


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)
