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
import tr.types
import tr.x_catawampus_tr181_2_0
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
CATA181MOCA = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.MoCA
MOCACTL = 'mocactl'
PYNETIFCONF = pynetlinux.ifconfig.Interface


# Regexps to parse mocactl output
MAC_RE = re.compile(r'^MAC Address\s+: ((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
PNC_RE = re.compile(r'Preferred NC\s+: (\d+)')
PTX_RE = re.compile(r'\ATxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
PRX_RE = re.compile(r'\ARxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps'
                    r'\s+(\d+[.]?\d*) dB')
RXB_RE = re.compile(r'\ARxBc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
QAM_RE = re.compile(r'256 QAM capable\s+:\s+(\d+)')
AGG_RE = re.compile(r'Aggregated PDUs\s+:\s+(\d+)')
BTL_RE = re.compile(r'\s*([0-9a-fA-F]{32})\s+([0-9a-fA-F]{32})')

TX_RE = re.compile(r'Unicast Tx Pkts To Node\s+: (\d+)')
RX_RE = re.compile(r'Unicast Rx Pkts From Node\s+: (\d+)')
E1_RE = re.compile(r'Rx CodeWord ErrorAndUnCorrected\s+: (\d+)')
E2_RE = re.compile(r'Rx NoSync Errors\s+: (\d+)')

NODE_RE = re.compile(r'\ANode\s*: (\d+)')


def IsMoca1_1():
  """Check for existence of the MoCA 1.1 utilities."""
  cmd = [MOCACTL, '--version']
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


def _CombineBitloading(bitlines):
  """Combine bitloading information into one string.

  Args:
    bitlines: a list of lines of bitloading info:
    00008888888888888888888888888888     00008888888888888888888888888888
    88888888888888888888888888888888     88888888888888888888888888888888
    88888888888888888888888888888888     88888888888888888888888888888888
    88888888888888888888000000000000     88888888888888888888000000000000
    00000000000008888888888888888888     00000000000008888888888888888888
    88888888888888888888888888888888     88888888888888888888888888888888
    88888888888888888888888888888888     88888888888888888888888888888888
    88888888888888888888888888888000     88888888888888888888888888888000

  Returns:
    a tuple of two contiguous strings, '00008888888...888888000',
    for the left-hand and right-hand bitloading.
  """

  left = []
  right = []
  for line in bitlines:
    (l, r) = line.split()
    left.append(l.strip())
    right.append(r.strip())
  return (''.join(left), ''.join(right))


class BrcmMocaInterface(BASE181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""

  # TODO(dgentry) Supposed to be read/write, but we don't disable yet.
  Enable = tr.types.ReadOnlyBool(True)
  Name = tr.types.ReadOnlyString('')
  # In theory LowerLayers is writeable, but it is nonsensical to write to it.
  LowerLayers = tr.types.ReadOnlyString('')

  MAX_NODES_MOCA1 = 8
  MAX_NODES_MOCA2 = 16
  MaxNodes = tr.types.ReadOnlyInt(0)

  Upstream = tr.types.ReadOnlyBool(False)

  def __init__(self, ifname, upstream=False, qfiles=None, numq=0, hipriq=0):
    BASE181MOCA.Interface.__init__(self)
    type(self).MaxNodes.Set(self, self.MAX_NODES_MOCA1)
    type(self).Name.Set(self, ifname)
    type(self).Upstream.Set(self, bool(upstream))
    self._pynet = PYNETIFCONF(ifname)
    self._qfiles = qfiles
    self._numq = numq
    self._hipriq = hipriq

    self.Unexport(['Alias', 'MaxBitRate', 'MaxIngressBW', 'MaxEgressBW',
                   'PreferredNC', 'PrivacyEnabledSetting', 'FreqCapabilityMask',
                   'FreqCurrentMaskSetting', 'FreqCurrentMask',
                   'KeyPassphrase', 'TxPowerLimit', 'PowerCntlPhyTarget',
                   'BeaconPowerLimit', 'NetworkTabooMask', 'NodeTabooMask',
                   'TxBcastRate', 'TxBcastPowerReduction'])
    self.Unexport(objects=['QoS'])

    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociatedDevices,
        getitem=self.GetAssociatedDeviceByIndex)

  @property
  def Stats(self):
    return BrcmMocaInterfaceStatsLinux26(self.Name, self._qfiles,
                                         self._numq, self._hipriq)

  @tr.session.cache
  def _MocaCtlShowStatus(self):
    """Return output of mocactl show --status."""
    mc = subprocess.Popen([MOCACTL, 'show', '--status'], stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  @tr.session.cache
  def _MocaCtlShowInitParms(self):
    """Return output of mocactl show --initparms."""
    mc = subprocess.Popen([MOCACTL, 'show', '--initparms'],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  @tr.session.cache
  def _MocaCtlShowConfig(self):
    """Return output of mocactl show --config."""
    mc = subprocess.Popen([MOCACTL, 'show', '--config'], stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  def _MocaCtlGetField(self, outfcn, field):
    """Look for one field in a mocactl command.

    ex: field='SwVersion' would return 5.6.789 from
    vendorId              : 999999999   HwVersion             : 0x12345678
    SwVersion             : 5.6.789     self MoCA Version     : 0x11

    Args:
      outfcn: a function to call, which must return a list of text lines.
      field: the text string to look for.
    Returns:
      The value of the field, or None.
    """

    m_re = re.compile(field + r'\s*:\s+(\S+)')
    for line in outfcn():
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
    up = self._MocaCtlGetField(self._MocaCtlShowStatus, 'linkUpTime').split(':')
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
    return self._pynet.get_mac()

  @property
  def FirmwareVersion(self):
    ver = self._MocaCtlGetField(self._MocaCtlShowStatus, 'SwVersion')
    return ver if ver else '0'

  def _RegToMoCA(self, regval):
    moca = {'0x10': '1.0', '0x11': '1.1', '0x20': '2.0', '0x21': '2.1'}
    return moca.get(regval, '0.0')

  @property
  def HighestVersion(self):
    reg = self._MocaCtlGetField(self._MocaCtlShowStatus, 'self MoCA Version')
    return self._RegToMoCA(reg)

  @property
  def CurrentVersion(self):
    reg = self._MocaCtlGetField(self._MocaCtlShowStatus, 'networkVersionNumber')
    return self._RegToMoCA(reg)

  @property
  def NetworkCoordinator(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'ncNodeId')
    return IntOrZero(nodeid)

  @property
  def NodeID(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'nodeId')
    return IntOrZero(nodeid)

  @property
  def BackupNC(self):
    bnc = nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'backupNcId')
    return bnc if bnc else ''

  @property
  def PrivacyEnabled(self):
    private = self._MocaCtlGetField(self._MocaCtlShowInitParms, 'Privacy')
    return True if private == 'enabled' else False

  @property
  def CurrentOperFreq(self):
    freq = self._MocaCtlGetField(self._MocaCtlShowStatus, 'rfChannel')
    if freq:
      mhz = IntOrZero(freq.split()[0])
      return int(mhz * 1e6)
    return 0

  @property
  def LastOperFreq(self):
    last = self._MocaCtlGetField(self._MocaCtlShowInitParms,
                                 'Nv Params - Last Oper Freq')
    if last:
      return IntOrZero(last.split()[0])
    return 0

  @property
  def QAM256Capable(self):
    qam = self._MocaCtlGetField(self._MocaCtlShowInitParms, 'qam256Capability')
    return True if qam == 'on' else False

  @property
  def PacketAggregationCapability(self):
    # example: "maxPktAggr   : 10 pkts"
    pkts = self._MocaCtlGetField(self._MocaCtlShowConfig, 'maxPktAggr')
    if pkts:
      return IntOrZero(pkts.split()[0])
    return 0

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  @tr.session.cache
  def _MocaCtlGetNodeIDs(self):
    """Return a list of active MoCA Node IDs."""
    mc = subprocess.Popen([MOCACTL, 'showtbl', '--nodestats'],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    nodes = set()
    for line in out.splitlines():
      node = NODE_RE.search(line)
      if node is not None:
        nodes.add(int(node.group(1)))
    return list(nodes)

  def GetAssociatedDevice(self, nodeid):
    """Get an AssociatedDevice object for the given NodeID."""
    ad = BrcmMocaAssociatedDevice(nodeid)
    if ad:
      ad.ValidateExports()
    return ad

  def IterAssociatedDevices(self):
    """Retrieves a list of all associated devices."""
    mocanodes = self._MocaCtlGetNodeIDs()
    for idx, nodeid in enumerate(mocanodes):
      yield idx, self.GetAssociatedDevice(nodeid)

  def GetAssociatedDeviceByIndex(self, index):
    mocanodes = self._MocaCtlGetNodeIDs()
    return self.GetAssociatedDevice(mocanodes[index])


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
  Active = tr.types.ReadOnlyBool(True)
  MACAddress = tr.types.ReadOnlyString('')
  NodeID = tr.types.ReadOnlyInt(-1)
  PacketAggregationCapability = tr.types.ReadOnlyInt(0)
  PHYTxRate = tr.types.ReadOnlyInt(0)
  PHYRxRate = tr.types.ReadOnlyInt(0)
  PreferredNC = tr.types.ReadOnlyBool(False)
  QAM256Capable = tr.types.ReadOnlyInt(0)
  RxBcastPowerLevel = tr.types.ReadOnlyInt(0)
  RxErroredAndMissedPackets = tr.types.ReadOnlyInt(0)
  RxPackets = tr.types.ReadOnlyInt(0)
  RxPowerLevel = tr.types.ReadOnlyInt(0)
  RxSNR = tr.types.ReadOnlyInt(0)
  TxBcastRate = tr.types.ReadOnlyInt(0)
  TxPackets = tr.types.ReadOnlyInt(0)
  TxPowerControlReduction = tr.types.ReadOnlyInt(0)
  X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm = tr.types.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxPowerLevel_dBm = tr.types.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxSNR_dB = tr.types.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxBitloading = tr.types.ReadOnlyString('')
  X_CATAWAMPUS_ORG_TxBitloading = tr.types.ReadOnlyString('')

  def __init__(self, nodeid):
    super(BrcmMocaAssociatedDevice, self).__init__()
    type(self).NodeID.Set(self, int(nodeid))
    self.Unexport(['HighestVersion'])

    self.ParseNodeStatus()
    self.ParseNodeStats()

  @tr.session.cache
  def ParseNodeStatus(self):
    """Run mocactl show --nodestatus for this node, parse the output."""
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestatus', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    bitloading = [[], []]
    bitloadidx = 0
    for line in out.splitlines():
      mac = MAC_RE.search(line)
      if mac is not None:
        type(self).MACAddress.Set(self, mac.group(1))
      pnc = PNC_RE.search(line)
      if pnc is not None:
        preferred = False if pnc.group(1) is '0' else True
        type(self).PreferredNC.Set(self, preferred)
      ptx = PTX_RE.search(line)
      if ptx is not None:
        type(self).PHYTxRate.Set(self, (IntOrZero(ptx.group(2)) / 1000000))
        txpowercontrol = int(FloatOrZero(ptx.group(1)))
        type(self).TxPowerControlReduction.Set(self, txpowercontrol)
      prx = PRX_RE.search(line)
      if prx is not None:
        type(self).PHYRxRate.Set(self, (IntOrZero(prx.group(2)) / 1000000))
        rxpower = FloatOrZero(prx.group(1))
        type(self).RxPowerLevel.Set(self, abs(int(rxpower)))
        type(self).X_CATAWAMPUS_ORG_RxPowerLevel_dBm.Set(self, rxpower)
        rxsnr = FloatOrZero(prx.group(3))
        type(self).RxSNR.Set(self, abs(int(rxsnr)))
        type(self).X_CATAWAMPUS_ORG_RxSNR_dB.Set(self, rxsnr)
      rxb = RXB_RE.search(line)
      if rxb is not None:
        type(self).TxBcastRate.Set(self, (IntOrZero(rxb.group(2)) / 1000000))
        rxbpower = FloatOrZero(rxb.group(1))
        type(self).RxBcastPowerLevel.Set(self, abs(int(rxbpower)))
        type(self).X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm.Set(self, rxbpower)
      qam = QAM_RE.search(line)
      if qam is not None:
        qam256 = False if qam.group(1) is '0' else True
        type(self).QAM256Capable.Set(self, qam256)
      agg = AGG_RE.search(line)
      if agg is not None:
        aggcapable = IntOrZero(agg.group(1))
        type(self).PacketAggregationCapability.Set(self, aggcapable)
      if 'Unicast Bit Loading Info' in line:
        bitloadidx = 0
      if 'Broadcast Bit Loading Info' in line:
        bitloadidx = 1
      btl = BTL_RE.search(line)
      if btl is not None:
        bitloading[bitloadidx].append(line)
    (txbitl, rxbitl) = _CombineBitloading(bitloading[0])
    type(self).X_CATAWAMPUS_ORG_RxBitloading.Set(self, '$BRCM1$' + rxbitl)
    type(self).X_CATAWAMPUS_ORG_TxBitloading.Set(self, '$BRCM1$' + txbitl)

  @tr.session.cache
  def ParseNodeStats(self):
    """Run mocactl show --nodestats for this node, parse the output."""
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestats', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    rx_err = 0
    for line in out.splitlines():
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
    type(self).RxErroredAndMissedPackets.Set(self, rx_err)


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)
