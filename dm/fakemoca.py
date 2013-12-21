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
# pylint: disable-msg=C6409

"""Implementation of fake tr-181 Device.MoCA objects.

Useful for uinit tests and for platform/fakecpe.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.core
import tr.tr181_v2_2
import tr.types

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

  BytesSent = tr.types.ReadOnlyUnsigned(1200)
  BytesReceived = tr.types.ReadOnlyUnsigned(1300)
  PacketsSent = tr.types.ReadOnlyUnsigned(1400)
  PacketsReceived = tr.types.ReadOnlyUnsigned(1500)
  ErrorsSent = tr.types.ReadOnlyUnsigned(2)
  ErrorsReceived = tr.types.ReadOnlyUnsigned(3)
  UnicastPacketsSent = tr.types.ReadOnlyUnsigned(1100000)
  UnicastPacketsReceived = tr.types.ReadOnlyUnsigned(2100000)
  DiscardPacketsSent = tr.types.ReadOnlyUnsigned(4)
  DiscardPacketsReceived = tr.types.ReadOnlyUnsigned(5)
  MulticastPacketsSent = tr.types.ReadOnlyUnsigned(1100)
  MulticastPacketsReceived = tr.types.ReadOnlyUnsigned(2100)
  BroadcastPacketsSent = tr.types.ReadOnlyUnsigned(11000)
  BroadcastPacketsReceived = tr.types.ReadOnlyUnsigned(21000)
  UnknownProtoPacketsReceived = tr.types.ReadOnlyUnsigned(6)


class FakeMocaInterface(BASE181MOCA.Interface):
  """tr181 Device.MoCA.Interface.Stats."""
  Enable = tr.types.Bool(True)
  BackupNC = tr.types.ReadOnlyUnsigned(7)
  BeaconPowerLimit = tr.types.Unsigned(8)
  CurrentOperFreq = tr.types.ReadOnlyUnsigned(1000)
  CurrentVersion = tr.types.ReadOnlyString('2.0')
  FirmwareVersion = tr.types.ReadOnlyString('1.0.2')
  FreqCapabilityMask = tr.types.ReadOnlyString('0x000000001FFFC000')
  FreqCurrentMaskSetting = tr.types.String('0x000000001FFFFFFF')
  HighestVersion = tr.types.ReadOnlyString('2.1')
  KeyPassphrase = tr.types.String('MocaKeyPassphrase')
  LastChange = tr.types.ReadOnlyUnsigned(1002)
  LastOperFreq = tr.types.ReadOnlyUnsigned(1003)
  LowerLayers = tr.types.ReadOnlyString('')
  MACAddress = tr.types.ReadOnlyMacAddr('00:11:22:33:44:00')
  MaxBitRate = tr.types.ReadOnlyUnsigned(300)
  MaxIngressBW = tr.types.ReadOnlyUnsigned(301)
  MaxEgressBW = tr.types.ReadOnlyUnsigned(302)
  MaxNodes = tr.types.ReadOnlyUnsigned(16)
  Name = tr.types.ReadOnlyString('eth1')
  NetworkCoordinator = tr.types.ReadOnlyUnsigned(3)
  NetworkTabooMask = tr.types.ReadOnlyString('0xffffffffffffffff')
  NodeID = tr.types.ReadOnlyUnsigned(1)
  NodeTabooMask = tr.types.ReadOnlyString('0x000fffffffffffff')
  PacketAggregationCapability = tr.types.ReadOnlyUnsigned(9)
  PowerCntlPhyTarget = tr.types.Unsigned(300)
  PreferredNC = tr.types.Bool(False)
  PrivacyEnabledSetting = tr.types.Bool(False)
  QAM256Capable = tr.types.ReadOnlyBool(True)
  Status = tr.types.ReadOnlyString('Up')
  TxBcastRate = tr.types.Unsigned(111)
  TxPowerLimit = tr.types.ReadOnlyUnsigned(4)
  TxBcastPowerReduction = tr.types.ReadOnlyUnsigned(5)
  Upstream = tr.types.ReadOnlyBool(False)

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
  Active = tr.types.Bool(True)
  HighestVersion = tr.types.ReadOnlyString('2.0')
  MACAddress = tr.types.ReadOnlyMacAddr('00:11:22:33:44:55')
  NodeID = tr.types.ReadOnlyUnsigned(1)
  PacketAggregationCapability = tr.types.ReadOnlyUnsigned(10)
  PHYRxRate = tr.types.ReadOnlyUnsigned(201)
  PHYTxRate = tr.types.ReadOnlyUnsigned(200)
  PreferredNC = tr.types.Bool(False)
  QAM256Capable = tr.types.Bool(True)
  RxBcastPowerLevel = tr.types.ReadOnlyUnsigned(22)
  RxPowerLevel = tr.types.ReadOnlyUnsigned(2)
  RxErroredAndMissedPackets = tr.types.ReadOnlyUnsigned(7)
  RxPackets = tr.types.ReadOnlyUnsigned(4000)
  RxSNR = tr.types.ReadOnlyUnsigned(3)
  TxBcastRate = tr.types.ReadOnlyUnsigned(75)
  TxPackets = tr.types.ReadOnlyUnsigned(3000)
  TxPowerControlReduction = tr.types.ReadOnlyUnsigned(3)

  def __init__(self, nodeid=None, mac=None):
    super(FakeMocaAssociatedDevice, self).__init__()
    if mac:
      type(self).MACAddress.Set(self, mac)
    if nodeid:
      type(self).NodeID.Set(self, int(nodeid))
