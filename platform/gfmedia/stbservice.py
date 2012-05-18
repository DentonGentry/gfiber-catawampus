#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-135 STBService.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import socket
import struct
import tr.tr135_v1_2


BASE135STB = tr.tr135_v1_2.STBService_v1_2.STBService
IGMPREGEX = re.compile('^\s+(\S+)\s+\d\s+\d:[0-9A-Fa-f]+\s+\d')
IGMP6REGEX = re.compile('^\d\s+\S+\s+([0-9A-Fa-f]{32})\s+\d\s+[0-9A-Fa-f]+\s+\d')
PROCNETIGMP = '/proc/net/igmp'
PROCNETIGMP6 = '/proc/net/igmp6'


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
    self.Unexport(objects='ServiceMonitoring')
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


def main():
  pass

if __name__ == '__main__':
  main()
