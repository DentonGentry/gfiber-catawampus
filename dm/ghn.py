#!/usr/bin/python
# Copyright 2017 Google Inc. All Rights Reserved.
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
#

"""Implement the tr181 G.HN data model.

All parameters have a description in catawampus/tr/schema/tr-181-2-4-0.xml
Values are read from '/tmp/ghn/config' which is regularly populated by
'ghn-periodic-stats'
"""

__author__ = 'germuth@google.com (Aaron Germuth)'

import google3

import tr.basemodel
import tr.cwmptypes

GHN_STATS_FILE = '/tmp/ghn/config'
BASE181GHN = tr.basemodel.Device.Ghn


def GetConfigValue(key, index=-1):
  with open(GHN_STATS_FILE) as f:
    lines = f.read().splitlines()
    # match all lines that contain the key
    # append an equals sign to avoid matching longer entries, for ex:
    # SYSTEM.GENERAL.FW_VERSION and SYSTEM.GENERAL.FW_VERSION_CORE
    matches = [x for x in lines if key + '=' in x]
    if not matches:
      print 'no matches was found in G.hn config file: %s' % GHN_STATS_FILE
      return None
    elif len(matches) > 1:
      print 'multiple matchess found in G.hn config file: %s' % GHN_STATS_FILE
      return None
    else:
      val = matches[0].split('=')[1]

      # if index was supplied, grab element from comma-separated-list
      if index != -1:
        val_list = val.split(',')
        if (0 > index) or (index >= len(val_list)):
          print 'list index out of range'
          return None
        val = val_list[index]

      # Try to determine what type we should return
      if val == 'YES':
        return True
      elif val == 'NO':
        return False
      elif val.isdigit():
        return int(val)
      else:
        return val


class GhnInterfaceAssociatedDevice(BASE181GHN.Interface.AssociatedDevice):
  """One Entry for each G.hn node connected to our local node.."""

  def __init__(self, device_id):
    super(GhnInterfaceAssociatedDevice, self).__init__()

    self.DeviceId = device_id

  @property
  def MACAddress(self):
    # List is ordered on device_id, device_id=0 is invalid
    return GetConfigValue('DIDMNG.GENERAL.MACS', self.DeviceId - 1)

  @property
  def TxPhyRate(self):
    # Formula taken from Spirit Configuration Tool source code
    val = GetConfigValue('DIDMNG.GENERAL.TX_BPS', self.DeviceId)
    return int(val) * 32 / 1000

  @property
  def RxPhyRate(self):
    # Formula taken from Spirit Configuration Tool source code
    val = GetConfigValue('DIDMNG.GENERAL.RX_BPS', self.DeviceId)
    return int(val) * 32 / 1000

  @property
  def Active(self):
    return GetConfigValue('DIDMNG.GENERAL.ACTIVE', self.DeviceId)


class GhnInterfaceStats(BASE181GHN.Interface.Stats):
  """Packet count information on eth1, we unexport every single parameter."""

  def __init__(self):
    super(GhnInterfaceStats, self).__init__()

    # Packet counts to/from G.hn can be seen with:
    # 'echo 1 > /sys/devices/platform/neta/gbe/cntrs'
    # and caught with turbogrinder instead
    self.Unexport(['BytesSent', 'BytesReceived', 'PacketsSent',
                   'PacketsReceived', 'ErrorsSent', 'ErrorsReceived',
                   'UnicastPacketsSent', 'UnicastPacketsReceived',
                   'DiscardPacketsSent', 'DiscardPacketsReceived',
                   'MulticastPacketsSent', 'MulticastPacketsReceived',
                   'BroadcastPacketsSent', 'BroadcastPacketsReceived',
                   'UnknownProtoPacketsReceived'])


class GhnInterface(BASE181GHN.Interface):
  """TR181 Ghn implementation for DS6923 optical module."""

  Upstream = tr.cwmptypes.ReadOnlyBool(False)
  ConnectionType = tr.cwmptypes.ReadOnlyString('Coax')
  Stats = GhnInterfaceStats()  # empty

  def __init__(self):
    super(GhnInterface, self).__init__()

    self.Unexport(['Status',  # Can't find equivalent inside configlayer
                              # NTP.GENERAL.STATUS doesn't match desc
                   'MaxBitRate',  # Can't find equivalent inside configlayer
                   'LowerLayers',  # tr181 "expected that it will not be used"
                   'NodeTypeDMConfig',  # Requests a node becomes domain_master
                   'TargetDomainNames'])  # Used for changing target domain_name
    self.Unexport(objects=['Stats'])

  @property
  def Enable(self):
    return GetConfigValue('NODE.GENERAL.ENABLE')

  @property
  def Alias(self):
    return GetConfigValue('NODE.GENERAL.DEVICE_ALIAS')

  @property
  def Name(self):
    return GetConfigValue('SYSTEM.PRODUCTION.DEVICE_NAME')

  @property
  def LastChange(self):
    return GetConfigValue('NODE.GENERAL.LAST_CHANGE')

  @property
  def MACAddress(self):
    return GetConfigValue('SYSTEM.PRODUCTION.MAC_ADDR')

  @property
  def FirmwareVersion(self):
    return GetConfigValue('SYSTEM.GENERAL.FW_VERSION')

  @property
  def DomainName(self):
    return GetConfigValue('NODE.GENERAL.DOMAIN_NAME')

  @property
  def DomainNameIdentifier(self):
    return GetConfigValue('NODE.GENERAL.DNI')

  @property
  def DomainId(self):
    return GetConfigValue('NODE.GENERAL.DOMAIN_ID')

  @property
  def DeviceId(self):
    return GetConfigValue('NODE.GENERAL.DEVICE_ID')

  @property
  def NodeTypeDMCapable(self):
    return GetConfigValue('SYSTEM.GENERAL.DOMAIN_MASTER_CAPABLE')

  @property
  def NodeTypeDMStatus(self):
    return GetConfigValue('NODE.GENERAL.NODE_TYPE') == 'DOMAIN_MASTER'

  @property
  def NodeTypeSCCapable(self):
    return GetConfigValue('SYSTEM.GENERAL.SEC_CONTROLLER_CAPABLE')

  @property
  def NodeTypeSCStatus(self):
    return GetConfigValue('SYSTEM.GENERAL.SEC_CONTROLLER_STATUS')

  @property
  def AssociatedDeviceNumberOfEntries(self):
    num_dids = GetConfigValue('DIDMNG.GENERAL.NUM_DIDS')
    if num_dids == 0:
      return 0
    else:
      # We don't count ourselves as an associated device
      return num_dids - 1

  @property
  def AssociatedDeviceList(self):
    current = 1
    neighbour_list = {}
    if self.AssociatedDeviceNumberOfEntries < 1:
      return neighbour_list

    # Grab all device Ids on record, and check each one
    ids = GetConfigValue('DIDMNG.GENERAL.DIDS').split(',')
    for id_str in ids:
      device_id = int(id_str)
      if device_id != self.DeviceId and device_id != 0:
        neighbour_list[str(current)] = GhnInterfaceAssociatedDevice(device_id)
        current += 1
    return neighbour_list


class Ghn(BASE181GHN):
  """Implementation of Ghn Module."""

  def __init__(self):
    super(Ghn, self).__init__()
    self.InterfaceList = {'1': GhnInterface()}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)
