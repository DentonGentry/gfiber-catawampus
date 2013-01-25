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

"""Implementation of tr-135 STBService."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import json
import re
import socket
import struct
import time

import tr.cwmpdate
import tr.session
import tr.tr135_v1_2
import tr.types
import tr.x_catawampus_videomonitoring_1_0 as vmonitor


BASE135STB = tr.tr135_v1_2.STBService_v1_2.STBService
CATA135STB = vmonitor.X_CATAWAMPUS_ORG_STBVideoMonitoring_v1_0.STBService
CATA135STBTOTAL = CATA135STB.ServiceMonitoring.MainStream.Total
IGMPREGEX = re.compile(r'^\s+(\S+)\s+\d\s+\d:[0-9A-Fa-f]+\s+\d')
IGMP6REGEX = re.compile((r'^\d\s+\S+\s+([0-9A-Fa-f]{32})\s+\d\s+[0-9A-Fa-f]'
                         r'+\s+\d'))
PROCNETIGMP = '/proc/net/igmp'
PROCNETIGMP6 = '/proc/net/igmp6'
PROCNETUDP = '/proc/net/udp'

CONT_MONITOR_FILES = [
    '/tmp/cwmp/monitoring/ts/tr_135_total_tsstats%d.json',
    '/tmp/cwmp/monitoring/dejittering/tr_135_total_djstats%d.json',
    '/tmp/cwmp/monitoring/tcp/tr_135_total_tcpstats%d.json']

EPG_STATS_FILES = ['/tmp/cwmp/monitoring/epg/tr_135_epg_stats*.json']
HDMI_STATS_FILE = '/tmp/cwmp/monitoring/hdmi/tr_135_hdmi_stats*.json'
HDMI_DISPLAY_DEVICE_STATS_FILES = [
    '/tmp/cwmp/monitoring/hdmi/tr_135_dispdev_status*.json',
    '/tmp/cwmp/monitoring/hdmi/tr_135_dispdev_stats*.json']


TIMENOW = time.time


def UnpackAlanCoxIP(packed):
  """Convert hex IP addresses to strings.

  /proc/net/igmp and /proc/net/udp both contain IP addresses printed as
  a hex string, _without_ calling ntohl() first.

  Example from /proc/net/udp on a little endian machine:
  sl  local_address rem_address   st tx_queue rx_queue ...
  464: 010002E1:07D0 00000000:0000 07 00000000:00000000 ...

  On a big-endian machine:
  sl  local_address rem_address   st tx_queue rx_queue ...
  464: E1020001:07D0 00000000:0000 07 00000000:00000000 ...

  Args:
    The hex thingy.
  Returns:
    A conventional dotted quad IP address encoding.
  """
  return socket.inet_ntop(socket.AF_INET, struct.pack('=L', int(packed, 16)))


class STBService(BASE135STB):
  """STBService.{i}."""

  def __init__(self):
    super(STBService, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport(objects='AVPlayers')
    self.Unexport(objects='AVStreams')
    self.Unexport(objects='Applications')
    self.Unexport(objects='Capabilities')
    self.Export(objects=['X_CATAWAMPUS-ORG_ProgramMetadata'])
    self.ServiceMonitoring = ServiceMonitoring()
    self.Components = Components()
    self.X_CATAWAMPUS_ORG_ProgramMetadata = ProgMetadata()


class Components(BASE135STB.Components):
  """STBService.{i}.Components."""

  def __init__(self):
    super(Components, self).__init__()
    self.Unexport('AudioDecoderNumberOfEntries')
    self.Unexport('AudioOutputNumberOfEntries')
    self.Unexport('CANumberOfEntries')
    self.Unexport('DRMNumberOfEntries')
    self.Unexport('SCARTNumberOfEntries')
    self.Unexport('SPDIFNumberOfEntries')
    self.Unexport('VideoDecoderNumberOfEntries')
    self.Unexport('VideoOutputNumberOfEntries')
    self.Unexport(objects='PVR')
    self.Unexport(lists='AudioDecoder')
    self.Unexport(lists='AudioOutput')
    self.Unexport(lists='CA')
    self.Unexport(lists='DRM')
    self.Unexport(lists='SCART')
    self.Unexport(lists='SPDIF')
    self.Unexport(lists='VideoDecoder')
    self.Unexport(lists='VideoOutput')
    self.FrontEndList = {'1': FrontEnd()}
    self.HDMIList = {'1': HDMI()}

  @property
  def FrontEndNumberOfEntries(self):
    return len(self.FrontEndList)

  @property
  def HDMINumberOfEntries(self):
    return len(self.HDMIList)


class FrontEnd(BASE135STB.Components.FrontEnd):
  """STBService.{i}.Components.FrontEnd.{i}."""

  def __init__(self):
    super(FrontEnd, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport('Name')
    self.Unexport('Status')
    self.Unexport(objects='DVBT')
    self.IP = IP()


class IP(BASE135STB.Components.FrontEnd.IP):
  """STBService.{i}.Components.FrontEnd.{i}.IP."""

  def __init__(self):
    super(IP, self).__init__()
    self.Unexport('ActiveInboundIPStreams')
    self.Unexport('ActiveOutboundIPStreams')
    self.Unexport('InboundNumberOfEntries')
    self.Unexport('OutboundNumberOfEntries')
    self.Unexport(objects='Dejittering')
    self.Unexport(objects='RTCP')
    self.Unexport(objects='RTPAVPF')
    self.Unexport(objects='ServiceConnect')
    self.Unexport(objects='FEC')
    self.Unexport(objects='ForceMonitor')
    self.Unexport(lists='Inbound')
    self.Unexport(lists='Outbound')
    self.IGMP = IGMP()


class IGMP(BASE135STB.Components.FrontEnd.IP.IGMP):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP."""

  def __init__(self):
    super(IGMP, self).__init__()
    self.Unexport('ClientGroupStatsNumberOfEntries')
    self.Unexport('ClientRobustness')
    self.Unexport('ClientUnsolicitedReportInterval')
    self.Unexport('ClientVersion')
    self.Unexport('DSCPMark')
    self.Unexport('Enable')
    self.Unexport('EthernetPriorityMark')
    self.Unexport('LoggingEnable')
    self.Unexport('MaximumNumberOfConcurrentGroups')
    self.Unexport('MaximumNumberOfTrackedGroups')
    self.Unexport('Status')
    self.Unexport('VLANIDMark')
    self.Unexport(lists='ClientGroupStats')
    self._ClientGroups = dict()

    self.ClientGroupList = tr.core.AutoDict(
        'ClientGroupList', iteritems=self.IterClientGroups,
        getitem=self.GetClientGroupByIndex)

  @property
  def ClientGroupNumberOfEntries(self):
    return len(self.ClientGroupList)

  def _ParseProcIgmp(self):
    """Get the list of multicast groups subscribed to.

    /proc/net/igmp uses an unusual format:
    Idx Device    : Count Querier       Group    Users Timer    Reporter
    1   lo        :     1      V3
                                010000E0     1 0:00000000           0
    2   eth0      :     1      V3
                                010000E0     1 0:00000000           0
    010000E0 is the IP multicast address as a hex number, and always
    big endian.

    Returns:
      a list of strings of the IP addresses of current IGMP group memberships.
    """
    igmp4s = set()
    igmp6s = set()
    with open(PROCNETIGMP, 'r') as f:
      for line in f:
        result = IGMPREGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          igmp4s.add(UnpackAlanCoxIP(igmp))
    with open(PROCNETIGMP6, 'r') as f:
      for line in f:
        result = IGMP6REGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          ip6 = ':'.join([igmp[0:4], igmp[4:8], igmp[8:12], igmp[12:16],
                          igmp[16:20], igmp[20:24], igmp[24:28], igmp[28:]])
          igmp6s.add(socket.inet_ntop(
              socket.AF_INET6, socket.inet_pton(socket.AF_INET6, ip6)))
    return sorted(list(igmp4s)) + sorted(list(igmp6s))

  def _UpdateClientGroups(self):
    """Maintain stable instance numbers for ClientGroups."""
    igmps = self._ParseProcIgmp()
    num_igmps = len(igmps)
    new_igmps = dict()
    old_igmps = self._ClientGroups

    # Existing ClientGroups keep their instance number in self._ClientGroups
    for instance, old_ipaddr in old_igmps.items():
      if old_ipaddr in igmps:
        new_igmps[instance] = old_ipaddr
        igmps.remove(old_ipaddr)

    # Remaining stream_ids claim an unused instance number in 1..num_streams
    assigned = set(new_igmps.keys())
    unassigned = set(range(1, num_igmps + 1)) - assigned
    for ipaddr in igmps:
      instance = unassigned.pop()
      new_igmps[instance] = ipaddr

    self._ClientGroups = new_igmps

  def GetClientGroup(self, ipaddr):
    return ClientGroup(ipaddr)

  def IterClientGroups(self):
    """Retrieves an iterable list of ClientGroups."""
    self._UpdateClientGroups()
    for key, ipaddr in self._ClientGroups.items():
      yield str(key), self.GetClientGroup(ipaddr)

  def GetClientGroupByIndex(self, index):
    """Directly access the value corresponding to a given key."""
    self._UpdateClientGroups()
    return self.GetClientGroup(self._ClientGroups[index])


class ClientGroup(BASE135STB.Components.FrontEnd.IP.IGMP.ClientGroup):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP.ClientGroup.{i}."""
  GroupAddress = tr.types.ReadOnlyString('')

  def __init__(self, ipaddr):
    super(ClientGroup, self).__init__()
    self.Unexport('Alias')
    self.Unexport('UpTime')
    type(self).GroupAddress.Set(self, ipaddr)


class HDMI(BASE135STB.Components.HDMI):
  """STBService.{i}.Components.HDMI."""
  ResolutionMode = tr.types.ReadOnlyString('Auto')

  def __init__(self):
    super(HDMI, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport('Name')
    self.Unexport('Status')
    self._UpdateStats()

  def _UpdateStats(self):
    """Read data in from JSON files."""
    data = dict()
    try:
      filename = HDMI_STATS_FILE
      with open(filename) as f:
        d = json.load(f)
        data.update(d['HDMIStats'])
    except IOError:
      # Its normal for the file to go away when the HDMI is not active.
      pass
    except (ValueError, KeyError) as e:
      # ValueError - JSON file is malformed and cannot be decoded
      # KeyError - Decoded JSON file doesn't contain the required fields.
      print('HDMIStats: Failed to read stats from file {0}, '
            'error = {1}'.format(filename, e))
    self.data = data

  @property
  def DisplayDevice(self):
    return HDMIDisplayDevice()

  @property
  def ResolutionValue(self):
    self._UpdateStats()
    return self.data.get('ResolutionValue', '')


class HDMIDisplayDevice(CATA135STB.Components.HDMI.DisplayDevice):
  """STBService.{i}.Components.HDMI.{i}.DisplayDevice."""

  def __init__(self):
    super(HDMIDisplayDevice, self).__init__()
    self.Unexport('CECSupport')
    self.data = self._UpdateStats()

  def _UpdateStats(self):
    data = dict()
    for wildcard in HDMI_DISPLAY_DEVICE_STATS_FILES:
      for filename in glob.glob(wildcard):
        try:
          with open(filename) as f:
            d = json.load(f)
            data.update(d['HDMIDisplayDevice'])
        except IOError:
          # Its normal for the file to go away when the HDMI is not active.
          pass
        except (ValueError, KeyError) as e:
          # ValueError - JSON file is malformed and cannot be decoded
          # KeyError - Decoded JSON file doesn't contain the required fields.
          print('HDMIDisplayDevice: Failed to read stats from file {0}, '
                'error = {1}'.format(filename, e))
    return data

  @property
  def Status(self):
    return self.data.get('Status', 'None')

  @property
  def Name(self):
    return self.data.get('Name', '')

  @property
  def SupportedResolutions(self):
    supported = self.data.get('SupportedResolutions', None)
    if supported:
      # There can be duplicates in the supported list.
      supportedset = set(supported)
      return ', '.join(sorted(supportedset))
    else:
      return ''

  @property
  def EEDID(self):
    return self.data.get('EEDID', '')

  @property
  def X_GOOGLE_COM_EDIDExtensions(self):
    extensions = self.data.get('EDIDExtensions', None)
    if extensions:
      return ', '.join(extensions)
    else:
      return ''

  @property
  def PreferredResolution(self):
    return self.data.get('PreferredResolution', '')

  @property
  def VideoLatency(self):
    return self.data.get('VideoLatency', 0)

  @property
  def AutoLipSyncSupport(self):
    return self.data.get('AutoLipSyncSupport', False)

  @property
  def HDMI3DPresent(self):
    return self.data.get('HDMI3DPresent', False)

  @property
  def X_GOOGLE_COM_NegotiationCount4(self):
    return self.data.get('Negotiations4hr', 0)

  @property
  def X_GOOGLE_COM_NegotiationCount24(self):
    return self.data.get('Negotiations24hr', 0)

  @property
  def X_GOOGLE_COM_VendorId(self):
    return self.data.get('VendorId', '')

  @property
  def X_GOOGLE_COM_ProductId(self):
    return self.data.get('ProductId', 0)

  @property
  def X_GOOGLE_COM_MfgYear(self):
    return self.data.get('MfgYear', 1990)

  @property
  def X_GOOGLE_COM_LastUpdateTimestamp(self):
    return tr.cwmpdate.format(float(self.data.get('LastUpdateTime', 0)))


class ServiceMonitoring(CATA135STB.ServiceMonitoring):
  """STBService.{i}.ServiceMonitoring."""

  def __init__(self):
    super(ServiceMonitoring, self).__init__()
    self.Unexport('FetchSamples')
    self.Unexport('ForceSample')
    self.Unexport('ReportEndTime')
    self.Unexport('ReportSamples')
    self.Unexport('ReportStartTime')
    self.Unexport('SampleEnable')
    self.Unexport('SampleInterval')
    self.Unexport('SampleState')
    self.Unexport('TimeReference')
    self.Unexport('EventsPerSampleInterval')
    self.Unexport(objects='GlobalOperation')
    self.stall_alarm_time = 0.0
    self.X_CATAWAMPUS_ORG_StallAlarmValue = 0
    self.MainStreamList = {}
    for x in range(1, 9):
      self.MainStreamList[x] = MainStream(x)
    # client-only MainStreams.
    self.MainStreamList[256] = MainStream(256)

  @property
  def MainStreamNumberOfEntries(self):
    return len(self.MainStreamList)

  def _CheckForStall(self):
    for ms in self.MainStreamList.values():
      mcast = ms.Total.X_CATAWAMPUS_ORG_MulticastStats
      threshold = self.X_CATAWAMPUS_ORG_StallAlarmValue
      if threshold and (mcast.StallTime > threshold):
        return True
    return False

  def GetAlarmTime(self):
    if not self.stall_alarm_time and self._CheckForStall():
      self.stall_alarm_time = TIMENOW()
    return tr.cwmpdate.format(self.stall_alarm_time)

  def SetAlarmTime(self, value):
    # We don't allow writing arbitrary time. Any write clears the alarm.
    self.stall_alarm_time = 0.0

  X_CATAWAMPUS_ORG_StallAlarmTime = property(
      GetAlarmTime, SetAlarmTime, None,
      'X_CATAWAMPUS_ORG_StallAlarmTime')


class MainStream(BASE135STB.ServiceMonitoring.MainStream):
  """STBService.{i}.ServiceMonitoring.MainStream."""

  def __init__(self, idx):
    super(MainStream, self).__init__()
    self.Unexport('AVStream')
    self.Unexport('Enable')
    self.Unexport('Gmin')
    self.Unexport('ServiceType')
    self.Unexport('SevereLossMinDistance')
    self.Unexport('SevereLossMinLength')
    self.Unexport('Status')
    self.Unexport('ChannelChangeFailureTimeout')
    self.Unexport('Alias')
    self.Unexport(objects='Sample')
    self.Total = Total(idx)


class Total(CATA135STBTOTAL):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total."""

  def __init__(self, idx):
    super(Total, self).__init__()
    self.idx = idx
    self.Unexport('Reset')
    self.Unexport('ResetTime')
    self.Unexport('TotalSeconds')
    self.Unexport(objects='AudioDecoderStats')
    self.Unexport(objects='RTPStats')
    self.Unexport(objects='VideoDecoderStats')
    self.Unexport(objects='VideoResponseStats')
    self.data = {}
    self.udp = {}

  @property
  def DejitteringStats(self):
    self._UpdateStats()
    return DejitteringStats(self.data.get('DejitteringStats', {}))

  @property
  def MPEG2TSStats(self):
    self._UpdateStats()
    return MPEG2TSStats(self.data.get('MPEG2TSStats', {}))

  @property
  def TCPStats(self):
    self._UpdateStats()
    return TCPStats(self.data.get('TCPStats', {}))

  @property
  def X_CATAWAMPUS_ORG_MulticastStats(self):
    self._UpdateStats()
    return MulticastStats(self.data.get('MulticastStats', {}), self.udp)

  def _UpdateProcNetUDP(self, udp):
    """Parse /proc/net/udp.

      sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt
      464: 010002E1:07D0 00000000:0000 07 00000000:00000000 00:00000000 00000000

      uid  timeout inode ref pointer drops
      0        0 6187 2 b1f64e00 0

    Args:
      a dict to store the parsed (rxq, drops) fields in.
    """
    with open(PROCNETUDP) as f:
      for line in f:
        try:
          line = ' '.join(line.split())
          fields = re.split('[ :]', line)
          ip = UnpackAlanCoxIP(fields[2])
          port = int(fields[3], 16)
          key = '%s:%d' % (ip, port)
          udp[key] = (int(fields[8], 16), int(fields[17]))  # rxq, drops
        except (ValueError, IndexError):
          # comment line, or something
          continue

  def _UpdateTotalStats(self, data):
    """Read stats in from JSON files."""
    for pattern in CONT_MONITOR_FILES:
      filename = pattern % self.idx
      try:
        with open(filename) as f:
          d = json.load(f)
        data.update(d['STBService'][0]['MainStream'][0])
      except IOError:
        # This is normal, file only exists if it is actively being used.
        pass
      except (ValueError, KeyError) as e:
        # ValueError - JSON file is malformed and cannot be decoded
        # KeyError - Decoded JSON file doesn't contain the required fields.
        print('ServiceMonitoring: Failed to read stats from file {0}, '
              'error = {1}'.format(filename, e))

  def _UpdateStats(self):
    self.data = {}
    self._UpdateTotalStats(self.data)
    self.udp = {}
    self._UpdateProcNetUDP(self.udp)


class DejitteringStats(BASE135STB.ServiceMonitoring.MainStream.Total.
                       DejitteringStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.DejitteringStats."""

  def __init__(self, data):
    super(DejitteringStats, self).__init__()
    self.data = data
    self.Unexport('TotalSeconds')

  @property
  def EmptyBufferTime(self):
    return int(self.data.get('EmptyBufferTime', 0))

  @property
  def Overruns(self):
    return int(self.data.get('Overruns', 0))

  @property
  def Underruns(self):
    return int(self.data.get('Underruns', 0))

  @property
  def X_GOOGLE_COM_SessionID(self):
    return int(self.data.get('SessionId', 0))


class MPEG2TSStats(BASE135STB.ServiceMonitoring.MainStream.Total.MPEG2TSStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.MPEG2TSStats."""

  def __init__(self, data):
    super(MPEG2TSStats, self).__init__()
    self.data = data
    self.Unexport('PacketDiscontinuityCounterBeforeCA')
    self.Unexport('TSSyncByteErrorCount')
    self.Unexport('TSSyncLossCount')
    self.Unexport('TotalSeconds')

  @property
  def PacketDiscontinuityCounter(self):
    return int(self.data.get('PacketDiscontinuityCounter', 0))

  @property
  def TSPacketsReceived(self):
    return int(self.data.get('TSPacketsReceived', 0))


class TCPStats(CATA135STB.ServiceMonitoring.MainStream.Total.TCPStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.TCPStats."""

  def __init__(self, data):
    super(TCPStats, self).__init__()
    self.data = data
    self.Unexport('TotalSeconds')

  @property
  def BytesReceived(self):
    return long(self.data.get('BytesReceived', 0))

  @property
  def PacketsReceived(self):
    return long(self.data.get('PacketsReceived', 0))

  @property
  def PacketsRetransmitted(self):
    return long(self.data.get('TotalRetransmits', 0))

  @property
  def X_CATAWAMPUS_ORG_BytesSent(self):
    return long(self.data.get('BytesSent', 0))

  @property
  def X_CATAWAMPUS_ORG_Cwnd(self):
    return long(self.data.get('Cwnd', 0))

  @property
  def X_CATAWAMPUS_ORG_SlowStartThreshold(self):
    return long(self.data.get('SSThresh', 0))

  @property
  def X_CATAWAMPUS_ORG_Unacked(self):
    return long(self.data.get('Unacked', 0))

  @property
  def X_CATAWAMPUS_ORG_Sacked(self):
    return long(self.data.get('Sacked', 0))

  @property
  def X_CATAWAMPUS_ORG_Lost(self):
    return long(self.data.get('Lost', 0))

  @property
  def X_CATAWAMPUS_ORG_Rtt(self):
    return long(self.data.get('Rtt', 0))

  @property
  def X_CATAWAMPUS_ORG_RttVariance(self):
    return long(self.data.get('RttVariance', 0))

  @property
  def X_CATAWAMPUS_ORG_ReceiveRTT(self):
    return long(self.data.get('ReceiveRTT', 0))

  @property
  def X_CATAWAMPUS_ORG_ReceiveSpace(self):
    return long(self.data.get('ReceiveSpace', 0))

  @property
  def X_CATAWAMPUS_ORG_RetransmitTimeout(self):
    return long(self.data.get('RetransTimeout', 0))


class MulticastStats(CATA135STBTOTAL.X_CATAWAMPUS_ORG_MulticastStats):
  """ServiceMonitoring.MainStream.{i}.Total.X_CATAWAMPUS_ORG_MulticastStats."""

  def __init__(self, data, udp):
    super(MulticastStats, self).__init__()
    self.data = data
    self.udp = udp

  @property
  def BPS(self):
    return int(self.data.get('bps', 0))

  @property
  def MulticastGroup(self):
    return str(self.data.get('MulticastGroup', ''))

  @property
  def StallTime(self):
    stalled = long(self.data.get('StalledUsecs', 0))
    return int(stalled / 1000)

  @property
  def StartupLatency(self):
    latency = long(self.data.get('StartupLagUsecs', 0))
    return int(latency / 1000)

  @property
  def MissedSchedule(self):
    schedule = int(self.data.get('MissingSchedule', 0))
    return schedule

  @property
  def UdpRxQueue(self):
    (rxq, _) = self.udp.get(self.MulticastGroup, (0, 0))
    return rxq

  @property
  def UdpDrops(self):
    (_, drops) = self.udp.get(self.MulticastGroup, (0, 0))
    return drops


class ProgMetadata(CATA135STB.X_CATAWAMPUS_ORG_ProgramMetadata):
  """STBService.{i}.X_CATAWAMPUS_ORG_ProgramMetadata."""

  def __init__(self):
    super(ProgMetadata, self).__init__()

  @property
  def EPG(self):
    return EPG()


class EPG(CATA135STB.X_CATAWAMPUS_ORG_ProgramMetadata.EPG):
  """STBService.{i}.X_CATAWAMPUS_ORG_ProgramMetadata.EPG."""

  def __init__(self):
    super(EPG, self).__init__()
    self.data = self._GetStats()

  def _GetStats(self):
    """Generate stats object from the JSON stats."""
    data = dict()
    for wildcard in EPG_STATS_FILES:
      for filename in glob.glob(wildcard):
        try:
          with open(filename) as f:
            d = json.load(f)
            data.update(d['EPGStats'])
        # IOError - Failed to open file or failed to read from file
        # ValueError - JSON file is malformed and cannot be decoded
        # KeyError - Decoded JSON file doesn't contain the required fields.
        except (IOError, ValueError, KeyError) as e:
          print('EPGStats: Failed to read stats from file {0}, '
                'error = {1}'.format(filename, e))
    return data

  @property
  def MulticastPackets(self):
    return self.data.get('MulticastPackets', 0)

  @property
  def EPGErrors(self):
    return self.data.get('EPGErrors', 0)

  @property
  def LastReceivedTime(self):
    last = self.data.get('LastReceivedTime', 0)
    return tr.cwmpdate.format(float(last))

  @property
  def EPGExpireTime(self):
    return tr.cwmpdate.format(float(self.data.get('EPGExpireTime', 0)))
