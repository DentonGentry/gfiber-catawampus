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
# pylint:disable=invalid-name

"""Implementation of tr-181 MoCA objects for Broadcom chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import json
import subprocess
import pynetlinux
import tr.session
import tr.tr181_v2_2
import tr.cwmpbool
import tr.cwmptypes
import tr.mainloop
import tr.x_catawampus_tr181_2_0
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
CATA181MOCA = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.MoCA
MOCAGLOBALJSON = '/tmp/cwmp/monitoring/moca2/globals'
MOCANODEJSON = '/tmp/cwmp/monitoring/moca2/node%d'
MOCAP = 'mocap'
MOCATRACE = ['mocatrace']
PYNETIFCONF = pynetlinux.ifconfig.Interface


def IsMoca2_0():
  """Check for existence of the MoCA 2.0 utilities."""
  cmd = [MOCAP, 'get', '--fw_version']
  try:
    rc = subprocess.call(cmd)
    return True if rc == 0 else False
  except OSError:
    return False


def _RegToMoCA(regval):
  moca = {'16': '1.0', '17': '1.1', '32': '2.0', '33': '2.1'}
  return moca.get(regval, '0.0')


class BrcmMocaInterface(CATA181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""
  Enable = tr.cwmptypes.ReadOnlyBool(True)
  Name = tr.cwmptypes.ReadOnlyString('')
  # In theory LowerLayers is writeable, but it is nonsensical to write to it.
  LowerLayers = tr.cwmptypes.ReadOnlyString('')

  MAX_NODES_MOCA1 = 8
  MAX_NODES_MOCA2 = 16
  MaxNodes = tr.cwmptypes.ReadOnlyInt(0)

  Upstream = tr.cwmptypes.ReadOnlyBool(False)

  def __init__(self, ifname, upstream=False, qfiles=None, numq=0, hipriq=0):
    super(BrcmMocaInterface, self).__init__()
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
                   'NetworkTabooMask', 'NodeTabooMask', 'TxBcastRate'])
    self.Unexport(objects=['QoS'])

  @property
  def Stats(self):
    return BrcmMocaInterfaceStatsLinux26(self.Name, self._qfiles,
                                         self._numq, self._hipriq)

  @tr.session.cache
  def _GetGlobalInfo(self):
    """Return MoCA state not associated with a particular node."""
    try:
      return json.load(open(MOCAGLOBALJSON))
    except (IOError, ValueError):
      return {}

  @property
  def BackupNC(self):
    return self._GetGlobalInfo().get(u'BackupNcNodeId', 0)

  @property
  def CurrentOperFreq(self):
    return self._GetGlobalInfo().get(u'Cof', 0) * 1000000

  @property
  def CurrentVersion(self):
    ver = str(self._GetGlobalInfo().get(u'MocaNetworkVersion', 0))
    return _RegToMoCA(ver)

  @property
  def FirmwareVersion(self):
    return self._GetGlobalInfo().get(u'FwVersion', '0')

  @property
  def HighestVersion(self):
    return self._GetGlobalInfo().get(u'MocaVersion', '0.0')

  @property
  def LastChange(self):
    """Return number of seconds the link has been up."""
    return self._GetGlobalInfo().get(u'LinkUptime', 0)

  @property
  def LastOperFreq(self):
    return self._GetGlobalInfo().get(u'Lof', 0) * 1000000

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def NetworkCoordinator(self):
    return self._GetGlobalInfo().get(u'NcNodeId', 0)

  @property
  def NodeID(self):
    return self._GetGlobalInfo().get(u'NodeId', 0)

  @property
  def PacketAggregationCapability(self):
    return self._GetGlobalInfo().get(u'PacketAggregation', 0)

  @property
  def PreferredNC(self):
    return bool(self._GetGlobalInfo().get(u'PreferredNc', 0))

  @property
  def PrivacyEnabled(self):
    return bool(self._GetGlobalInfo().get(u'PrivacyEn', False))

  @property
  def QAM256Capable(self):
    return bool(self._GetGlobalInfo().get(u'Qam256', False))

  @property
  def Status(self):
    if not self._pynet.is_up():
      return 'Down'
    (_, _, _, link_up) = self._pynet.get_link_info()
    if link_up:
      return 'Up'
    else:
      return 'Dormant'

  @property
  def TxBcastPowerReduction(self):
    return self._GetGlobalInfo().get(u'TxBcastPowerReduction', 0)

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  @property
  @tr.session.cache
  def AssociatedDeviceList(self):
    """Return active MoCA nodes."""
    result = {}
    idx = 1
    for x in range(17):
      try:
        filename = MOCANODEJSON % x
        node = json.load(open(filename))
        mac = node.get(u'MACAddress', u'00:00:00:00:00:00')
      except (IOError, ValueError):
        continue
      if mac is not None and mac != u'00:00:00:00:00:00':
        result[str(idx)] = BrcmMocaAssociatedDevice(node)
        idx += 1
    return result

  def GetExtraTracing(self):
    mt = subprocess.Popen(MOCATRACE, stdout=subprocess.PIPE)
    out, _ = mt.communicate(None)
    return False if 'false' in out else True

  @tr.mainloop.WaitUntilIdle
  def _WriteTracing(self, enb):
    cmd = MOCATRACE + [enb]
    rc = subprocess.call(cmd)
    if rc:
      print '%s failed, exit code:%d' % (str(cmd), rc)

  def SetExtraTracing(self, value):
    enb = 'true' if tr.cwmpbool.parse(value) else 'false'
    self._WriteTracing(enb)

  X_CATAWAMPUS_ORG_ExtraTracing = property(
      GetExtraTracing, SetExtraTracing, None,
      'Device.MoCA.Interface.{i}.X_CATAWAMPUS-ORG_ExtraTracing')


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
  HighestVersion = tr.cwmptypes.ReadOnlyString('')
  MACAddress = tr.cwmptypes.ReadOnlyString('')
  NodeID = tr.cwmptypes.ReadOnlyInt(-1)
  PHYRxRate = tr.cwmptypes.ReadOnlyUnsigned(0)
  PHYTxRate = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxBcastPowerLevel = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxErroredAndMissedPackets = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxPackets = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxPowerLevel = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxSNR = tr.cwmptypes.ReadOnlyUnsigned(0)
  TxBcastRate = tr.cwmptypes.ReadOnlyUnsigned(0)
  TxPackets = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxPowerLevel_dBm = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_RxSNR_dB = tr.cwmptypes.ReadOnlyFloat(0.0)
  X_CATAWAMPUS_ORG_TxBitloading = tr.cwmptypes.ReadOnlyString('')
  X_CATAWAMPUS_ORG_RxBitloading = tr.cwmptypes.ReadOnlyString('')
  X_CATAWAMPUS_ORG_RxPrimaryCwCorrected = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxPrimaryCwUncorrected = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxPrimaryCwNoErrors = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxPrimaryCwNoSync = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxSecondaryCwCorrected = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxSecondaryCwUncorrected = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxSecondaryCwNoErrors = tr.cwmptypes.ReadOnlyUnsigned(0)
  X_CATAWAMPUS_ORG_RxSecondaryCwNoSync = tr.cwmptypes.ReadOnlyUnsigned(0)

  def __init__(self, node):
    super(BrcmMocaAssociatedDevice, self).__init__()
    self.Unexport(['PacketAggregationCapability', 'PreferredNC',
                   'QAM256Capable', 'TxPowerControlReduction'])
    mac = node.get(u'MACAddress', u'00:00:00:00:00:00')
    type(self).MACAddress.Set(self, mac)
    version = str(node.get(u'MocaVersion', 0))
    type(self).HighestVersion.Set(self, _RegToMoCA(version))
    type(self).NodeID.Set(self, node.get(u'NodeId', 0))
    type(self).PHYRxRate.Set(self, node.get(u'PHYRxRate', 0))
    type(self).PHYTxRate.Set(self, node.get(u'PHYTxRate', 0))
    rxbcast = node.get(u'RxBroadcastPower', 0.0)
    type(self).RxBcastPowerLevel.Set(self, abs(int(rxbcast)))
    missed = node.get(u'RxErroredAndMissedPackets', 0)
    type(self).RxErroredAndMissedPackets.Set(self, missed)
    type(self).RxPackets.Set(self, node.get(u'RxPackets', 0))
    rxpower = node.get(u'RxPower', 0.0)
    type(self).RxPowerLevel.Set(self, abs(int(rxpower)))
    type(self).RxSNR.Set(self, int(node.get(u'RxSNR', 0.0)))
    type(self).TxBcastRate.Set(self, node.get(u'PHYTxBroadcastRate', 0))
    type(self).TxPackets.Set(self, node.get(u'TxPackets', 0))
    type(self).X_CATAWAMPUS_ORG_RxBcastPowerLevel_dBm.Set(self, rxbcast)
    type(self).X_CATAWAMPUS_ORG_RxPowerLevel_dBm.Set(self, rxpower)
    type(self).X_CATAWAMPUS_ORG_RxSNR_dB.Set(self, node.get(u'RxSNR', 0.0))
    bitl = node.get(u'TxBitloading', '')
    type(self).X_CATAWAMPUS_ORG_TxBitloading.Set(self, bitl)
    bitl = node.get(u'RxBitloading', '')
    type(self).X_CATAWAMPUS_ORG_RxBitloading.Set(self, bitl)
    c = node.get(u'RxPrimaryCwCorrected', 0)
    type(self).X_CATAWAMPUS_ORG_RxPrimaryCwCorrected.Set(self, c)
    c = node.get(u'RxPrimaryCwUncorrected', 0)
    type(self).X_CATAWAMPUS_ORG_RxPrimaryCwUncorrected.Set(self, c)
    c = node.get(u'RxPrimaryCwNoErrors', 0)
    type(self).X_CATAWAMPUS_ORG_RxPrimaryCwNoErrors.Set(self, c)
    c = node.get(u'RxPrimaryCwNoSync', 0)
    type(self).X_CATAWAMPUS_ORG_RxPrimaryCwNoSync.Set(self, c)
    c = node.get(u'RxSecondaryCwCorrected', 0)
    type(self).X_CATAWAMPUS_ORG_RxSecondaryCwCorrected.Set(self, c)
    c = node.get(u'RxSecondaryCwUncorrected', 0)
    type(self).X_CATAWAMPUS_ORG_RxSecondaryCwUncorrected.Set(self, c)
    c = node.get(u'RxSecondaryCwNoErrors', 0)
    type(self).X_CATAWAMPUS_ORG_RxSecondaryCwNoErrors.Set(self, c)
    c = node.get(u'RxSecondaryCwNoSync', 0)
    type(self).X_CATAWAMPUS_ORG_RxSecondaryCwNoSync.Set(self, c)


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  InterfaceNumberOfEntries = tr.cwmptypes.NumberOf('InterfaceList')

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}
