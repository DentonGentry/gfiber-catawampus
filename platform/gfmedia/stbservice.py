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
#pylint: disable-msg=C6409

"""Implementation of tr-135 STBService."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import json
import re
import socket
import struct
import tr.tr135_v1_2


BASE135STB = tr.tr135_v1_2.STBService_v1_2.STBService
IGMPREGEX = re.compile('^\s+(\S+)\s+\d\s+\d:[0-9A-Fa-f]+\s+\d')
IGMP6REGEX = re.compile(('^\d\s+\S+\s+([0-9A-Fa-f]{32})\s+\d\s+[0-9A-Fa-f]'
                         '+\s+\d'))
PROCNETIGMP = '/proc/net/igmp'
PROCNETIGMP6 = '/proc/net/igmp6'
# TODO(binesh):
# This is currently a place holder and needs update once the list is finalised.
# List the files to read the servicemonitoring stats from.
CONT_MONITOR_FILES = ['/tmp/cwmp/tr135_mp2ts_stats.json']


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
    self.ServiceMonitoring = STBServiceMonitoring()
    self.Components = STBComponents()


class STBComponents(BASE135STB.Components):
  """STBService.{i}.Components."""

  def __init__(self):
    super(STBComponents, self).__init__()
    self.Unexport('AudioDecoderNumberOfEntries')
    self.Unexport('AudioOutputNumberOfEntries')
    self.Unexport('CANumberOfEntries')
    self.Unexport('DRMNumberOfEntries')
    self.Unexport('HDMINumberOfEntries')
    self.Unexport('SCARTNumberOfEntries')
    self.Unexport('SPDIFNumberOfEntries')
    self.Unexport('VideoDecoderNumberOfEntries')
    self.Unexport('VideoOutputNumberOfEntries')
    self.Unexport(objects='PVR')
    self.Unexport(lists='AudioDecoder')
    self.Unexport(lists='AudioOutput')
    self.Unexport(lists='CA')
    self.Unexport(lists='DRM')
    self.Unexport(lists='HDMI')
    self.Unexport(lists='SCART')
    self.Unexport(lists='SPDIF')
    self.Unexport(lists='VideoDecoder')
    self.Unexport(lists='VideoOutput')
    self.FrontEndList = {'1': STBFrontEnd()}

  @property
  def FrontEndNumberOfEntries(self):
    return len(self.FrontEndList)


class STBFrontEnd(BASE135STB.Components.FrontEnd):
  """STBService.{i}.Components.FrontEnd.{i}."""

  def __init__(self):
    super(STBFrontEnd, self).__init__()
    self.Unexport('Enable')
    self.Unexport('Name')
    self.Unexport('Status')
    self.Unexport(objects='DVBT')
    self.IP = STBIP()


class STBIP(BASE135STB.Components.FrontEnd.IP):
  """STBService.{i}.Components.FrontEnd.{i}.IP."""

  def __init__(self):
    super(STBIP, self).__init__()
    self.Unexport('ActiveInboundIPStreams')
    self.Unexport('ActiveOutboundIPStreams')
    self.Unexport('InboundNumberOfEntries')
    self.Unexport('OutboundNumberOfEntries')
    self.Unexport(objects='Dejittering')
    self.Unexport(objects='RTCP')
    self.Unexport(objects='RTPAVPF')
    self.Unexport(objects='ServiceConnect')
    self.Unexport(lists='Inbound')
    self.Unexport(lists='Outbound')
    self.IGMP = STBIGMP()


class STBIGMP(BASE135STB.Components.FrontEnd.IP.IGMP):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP."""

  def __init__(self):
    super(STBIGMP, self).__init__()
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

    self.ClientGroupList = tr.core.AutoDict(
        'ClientGroupList', iteritems=self.IterClientGroups,
        getitem=self.GetClientGroupByIndex)

  @property
  def ClientGroupNumberOfEntries(self):
    return len(self.ClientGroupList)

  def _ParseProcIgmp(self):
    """Returns a list of current IGMP group memberships.

    /proc/net/igmp uses an unusual format:
    Idx Device    : Count Querier       Group    Users Timer    Reporter
    1   lo        :     1      V3
                                010000E0     1 0:00000000           0
    2   eth0      :     1      V3
                                010000E0     1 0:00000000           0
    010000E0 is the IP multicast address as a hex number, and always
    big endian.
    """
    igmps = set()
    with open(PROCNETIGMP, 'r') as f:
      for line in f:
        result = IGMPREGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          igmps.add(socket.inet_ntop(
              socket.AF_INET, struct.pack('<L', int(igmp, 16))))
    with open(PROCNETIGMP6, 'r') as f:
      for line in f:
        result = IGMP6REGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          ip6 = ':'.join([igmp[0:4], igmp[4:8], igmp[8:12], igmp[12:16],
                          igmp[16:20], igmp[20:24], igmp[24:28], igmp[28:]])
          igmps.add(socket.inet_ntop(socket.AF_INET6,
                                     socket.inet_pton(socket.AF_INET6, ip6)))
    return list(igmps)

  def GetClientGroup(self, ipaddr):
    return STBClientGroup(ipaddr)

  def IterClientGroups(self):
    """Retrieves a list of IGMP memberships."""
    igmps = self._ParseProcIgmp()
    for idx, ipaddr in enumerate(igmps, start=1):
      yield str(idx), self.GetClientGroup(ipaddr)

  def GetClientGroupByIndex(self, index):
    igmps = self._ParseProcIgmp()
    i = int(index) - 1
    if i > len(igmps):
      raise IndexError('No such object ClientGroup.{0}'.format(index))
    return self.GetClientGroup(igmps[i])


class STBClientGroup(BASE135STB.Components.FrontEnd.IP.IGMP.ClientGroup):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP.ClientGroup.{i}."""

  def __init__(self, ipaddr):
    super(STBClientGroup, self).__init__()
    self.Unexport('UpTime')
    self.ipaddr = ipaddr

  @property
  def GroupAddress(self):
    return self.ipaddr


class STBServiceMonitoring(BASE135STB.ServiceMonitoring):
  """STBService.{i}.ServiceMonitoring."""

  def __init__(self):
    super(STBServiceMonitoring, self).__init__()
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
    self._MainStreamStats = dict()
    self.MainStreamList = tr.core.AutoDict(
        'MainStreamList', iteritems=self.IterMainStreams,
        getitem=self.GetMainStreamByIndex)

  @property
  def MainStreamNumberOfEntries(self):
    return len(self.MainStreamList)

  def UpdateSvcMonitorStats(self):
    """Retrieve and aggregate stats from all related JSON stats files."""
    for filename in CONT_MONITOR_FILES:
      self.DeserializeStats(filename)

  def ReadJSONStats(self, fname):
    """Retrieves statistics from the service monitoring JSON file."""
    d = None
    with open(fname) as f:
      d = json.load(f)
    return d

  def DeserializeStats(self, fname):
    """Generate stats object from the JSON stats."""
    try:
      d = self.ReadJSONStats(fname)
      streams = d['STBService'][0]['MainStream']
      for i in range(len(streams)):
        sid = streams[i]['StreamId']
        if sid not in self._MainStreamStats.keys():
          self._MainStreamStats[sid] = STBMainStream()
        self._MainStreamStats[sid].UpdateMainstreamStats(streams[i])

    # IOError - Failed to open file or failed to read from file
    # ValueError - JSON file is malformed and cannot be decoded
    # KeyError - Decoded JSON file doesn't contain the required fields.
    except (IOError, ValueError, KeyError) as e:
      print('ServiceMonitoring: Failed to read stats from file {0}, '
            'error = {1}'.format(fname, e))

  def IterMainStreams(self):
    """Retrieves an iterable list of stats."""
    self.UpdateSvcMonitorStats()
    return self._MainStreamStats.items()

  def GetMainStreamByIndex(self, index):
    """Directly access the value corresponding to a given key."""
    self.UpdateSvcMonitorStats()
    return self._MainStreamStats[index]


class STBMainStream(BASE135STB.ServiceMonitoring.MainStream):
  """STBService.{i}.ServiceMonitoring.MainStream."""

  def __init__(self):
    super(STBMainStream, self).__init__()
    self.Unexport('AVStream')
    self.Unexport('Enable')
    self.Unexport('Gmin')
    self.Unexport('ServiceType')
    self.Unexport('SevereLossMinDistance')
    self.Unexport('SevereLossMinLength')
    self.Unexport('Status')
    self.Unexport('ChannelChangeFailureTimeout')
    self.Unexport(objects='Sample')
    self.Total = STBTotal()

  def UpdateMainstreamStats(self, data):
    self.Total.UpdateTotalStats(data)


class STBTotal(BASE135STB.ServiceMonitoring.MainStream.Total):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total."""

  def __init__(self):
    super(STBTotal, self).__init__()
    self.Unexport('Reset')
    self.Unexport('ResetTime')
    self.Unexport('TotalSeconds')
    self.Unexport(objects='AudioDecoderStats')
    self.Unexport(objects='RTPStats')
    self.Unexport(objects='VideoDecoderStats')
    self.Unexport(objects='VideoResponseStats')
    self.DejitteringStats = STBDejitteringStats()
    self.MPEG2TSStats = STBMPEG2TSStats()
    self.TCPStats = STBTCPStats()

  def UpdateTotalStats(self, data):
    if 'DejitteringStats' in data.keys():
      self.DejitteringStats.UpdateDejitteringStats(data['DejitteringStats'])
    if 'MPEG2TSStats' in data.keys():
      self.MPEG2TSStats.UpdateMPEG2TSStats(data['MPEG2TSStats'])
    if 'TCPStats' in data.keys():
      self.TCPStats.UpdateTCPStats(data['TCPStats'])


class STBDejitteringStats(BASE135STB.ServiceMonitoring.MainStream.Total.
                          DejitteringStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.DejitteringStats."""

  def __init__(self):
    super(STBDejitteringStats, self).__init__()
    self.Unexport('TotalSeconds')
    self._empty_buffer_time = 0
    self._overruns = 0
    self._underruns = 0

  @property
  def EmptyBufferTime(self):
    return self._empty_buffer_time

  @property
  def Overruns(self):
    return self._overruns

  @property
  def Underruns(self):
    return self._underruns

  def UpdateDejitteringStats(self, djstats):
    if 'EmptyBufferTime' in djstats.keys():
      self._empty_buffer_time = djstats['EmptyBufferTime']
    if 'Overruns' in djstats.keys():
      self._overruns = djstats['Overruns']
    if 'Underruns' in djstats.keys():
      self._underruns = djstats['Underruns']


class STBMPEG2TSStats(BASE135STB.ServiceMonitoring.MainStream.Total.
                      MPEG2TSStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.MPEG2TSStats."""

  def __init__(self):
    super(STBMPEG2TSStats, self).__init__()
    self.Unexport('PacketDiscontinuityCounterBeforeCA')
    self.Unexport('TSSyncByteErrorCount')
    self.Unexport('TSSyncLossCount')
    self.Unexport('TotalSeconds')
    self._packet_discont_counter = 0
    self._ts_packets_received = 0

  @property
  def PacketDiscontinuityCounter(self):
    return self._packet_discont_counter

  @property
  def TSPacketsReceived(self):
    return self._ts_packets_received

  def UpdateMPEG2TSStats(self, tsstats):
    if 'PacketsDiscontinuityCounter' in tsstats.keys():
      self._packet_discont_counter = tsstats['PacketsDiscontinuityCounter']
    if 'TSPacketsReceived' in tsstats.keys():
      self._ts_packets_received = tsstats['TSPacketsReceived']


class STBTCPStats(BASE135STB.ServiceMonitoring.MainStream.Total.TCPStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.TCPStats."""

  def __init__(self):
    super(STBTCPStats, self).__init__()
    self.Unexport('TotalSeconds')
    self._bytes_received = 0
    self._packets_received = 0
    self._packets_retransmitted = 0

  @property
  def BytesReceived(self):
    return self._bytes_received

  @property
  def PacketsReceived(self):
    return self._packets_received

  @property
  def PacketsRetransmitted(self):
    return self._packets_retransmitted

  def UpdateTCPStats(self, tcpstats):
    if 'Bytes Received' in tcpstats.keys():
      self._bytes_received = tcpstats['Bytes Received']
    if 'Packets Received' in tcpstats.keys():
      self._packets_received = tcpstats['Packets Received']
    if 'Packets Retransmitted' in tcpstats.keys():
      self._packets_retransmitted = tcpstats['Packets Retransmitted']


def main():
  pass

if __name__ == '__main__':
  main()
