#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Implementation of fake tr-181 Device.MoCA objects.

Useful for uinit tests and for platform/fakecpe.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.core
import tr.tr181_v2_2
import tr.cwmptypes

BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA


class FakeMoca(BASE181MOCA):
  """A fake implementation of tr181 Device.MoCA."""

  def __init__(self):
    super(FakeMoca, self).__init__()
    self.InterfaceList = {
        '1': FakeMocaInterface(),
    }

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


class FakeMocaInterfaceStats(BASE181MOCA.Interface.Stats):
  """tr181 Device.MoCA.Interface.Stats."""

  BytesSent = tr.cwmptypes.ReadOnlyUnsigned(1200)
  BytesReceived = tr.cwmptypes.ReadOnlyUnsigned(1300)
  PacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1400)
  PacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(1500)
  ErrorsSent = tr.cwmptypes.ReadOnlyUnsigned(2)
  ErrorsReceived = tr.cwmptypes.ReadOnlyUnsigned(3)
  UnicastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1100000)
  UnicastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(2100000)
  DiscardPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(4)
  DiscardPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(5)
  MulticastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(1100)
  MulticastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(2100)
  BroadcastPacketsSent = tr.cwmptypes.ReadOnlyUnsigned(11000)
  BroadcastPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(21000)
  UnknownProtoPacketsReceived = tr.cwmptypes.ReadOnlyUnsigned(6)


class FakeMocaInterface(BASE181MOCA.Interface):
  """tr181 Device.MoCA.Interface.Stats."""
  Enable = tr.cwmptypes.Bool(True)
  BackupNC = tr.cwmptypes.ReadOnlyUnsigned(7)
  BeaconPowerLimit = tr.cwmptypes.Unsigned(8)
  CurrentOperFreq = tr.cwmptypes.ReadOnlyUnsigned(1000)
  CurrentVersion = tr.cwmptypes.ReadOnlyString('2.0')
  FirmwareVersion = tr.cwmptypes.ReadOnlyString('1.0.2')
  FreqCapabilityMask = tr.cwmptypes.ReadOnlyString('0x000000001FFFC000')
  FreqCurrentMaskSetting = tr.cwmptypes.String('0x000000001FFFFFFF')
  HighestVersion = tr.cwmptypes.ReadOnlyString('2.1')
  KeyPassphrase = tr.cwmptypes.String('MocaKeyPassphrase')
  LastChange = tr.cwmptypes.ReadOnlyUnsigned(1002)
  LastOperFreq = tr.cwmptypes.ReadOnlyUnsigned(1003)
  LowerLayers = tr.cwmptypes.ReadOnlyString('')
  MACAddress = tr.cwmptypes.ReadOnlyMacAddr('00:11:22:33:44:00')
  MaxBitRate = tr.cwmptypes.ReadOnlyUnsigned(300)
  MaxIngressBW = tr.cwmptypes.ReadOnlyUnsigned(301)
  MaxEgressBW = tr.cwmptypes.ReadOnlyUnsigned(302)
  MaxNodes = tr.cwmptypes.ReadOnlyUnsigned(16)
  Name = tr.cwmptypes.ReadOnlyString('eth1')
  NetworkCoordinator = tr.cwmptypes.ReadOnlyUnsigned(3)
  NetworkTabooMask = tr.cwmptypes.ReadOnlyString('0xffffffffffffffff')
  NodeID = tr.cwmptypes.ReadOnlyUnsigned(1)
  NodeTabooMask = tr.cwmptypes.ReadOnlyString('0x000fffffffffffff')
  PacketAggregationCapability = tr.cwmptypes.ReadOnlyUnsigned(9)
  PowerCntlPhyTarget = tr.cwmptypes.Unsigned(300)
  PreferredNC = tr.cwmptypes.Bool(False)
  PrivacyEnabledSetting = tr.cwmptypes.Bool(False)
  QAM256Capable = tr.cwmptypes.ReadOnlyBool(True)
  Status = tr.cwmptypes.ReadOnlyString('Up')
  TxBcastRate = tr.cwmptypes.Unsigned(111)
  TxPowerLimit = tr.cwmptypes.ReadOnlyUnsigned(4)
  TxBcastPowerReduction = tr.cwmptypes.ReadOnlyUnsigned(5)
  Upstream = tr.cwmptypes.ReadOnlyBool(False)

  def __init__(self):
    super(FakeMocaInterface, self).__init__()
    self.Unexport(['Alias'])
    self.Unexport(objects=['QoS'])
    self.AssociatedDeviceList = {
        '1': FakeMocaAssociatedDevice(nodeid=1, mac='00:11:22:33:44:11'),
        '2': FakeMocaAssociatedDevice(nodeid=2, mac='00:11:22:33:44:22'),
    }

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  @property
  def Stats(self):
    return FakeMocaInterfaceStats()

  @property
  def FreqCurrentMask(self):
    return self.FreqCurrentMaskSetting

  @property
  def PrivacyEnabled(self):
    return self.PrivacyEnabledSetting


class FakeMocaAssociatedDevice(BASE181MOCA.Interface.AssociatedDevice):
  Active = tr.cwmptypes.Bool(True)
  HighestVersion = tr.cwmptypes.ReadOnlyString('2.0')
  MACAddress = tr.cwmptypes.ReadOnlyMacAddr('00:11:22:33:44:55')
  NodeID = tr.cwmptypes.ReadOnlyUnsigned(1)
  PacketAggregationCapability = tr.cwmptypes.ReadOnlyUnsigned(10)
  PHYRxRate = tr.cwmptypes.ReadOnlyUnsigned(201)
  PHYTxRate = tr.cwmptypes.ReadOnlyUnsigned(200)
  PreferredNC = tr.cwmptypes.Bool(False)
  QAM256Capable = tr.cwmptypes.Bool(True)
  RxBcastPowerLevel = tr.cwmptypes.ReadOnlyUnsigned(22)
  RxPowerLevel = tr.cwmptypes.ReadOnlyUnsigned(2)
  RxErroredAndMissedPackets = tr.cwmptypes.ReadOnlyUnsigned(7)
  RxPackets = tr.cwmptypes.ReadOnlyUnsigned(4000)
  RxSNR = tr.cwmptypes.ReadOnlyUnsigned(3)
  TxBcastRate = tr.cwmptypes.ReadOnlyUnsigned(75)
  TxPackets = tr.cwmptypes.ReadOnlyUnsigned(3000)
  TxPowerControlReduction = tr.cwmptypes.ReadOnlyUnsigned(3)

  def __init__(self, nodeid=None, mac=None):
    super(FakeMocaAssociatedDevice, self).__init__()
    if mac:
      type(self).MACAddress.Set(self, mac)
    if nodeid:
      type(self).NodeID.Set(self, int(nodeid))
