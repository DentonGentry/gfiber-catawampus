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

# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409

"""Unit tests for stbservice.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import socket
import struct
import unittest

import google3
import tr.session
import stbservice


def MockTime():
  return 1357898400.0


class MockIoloop(object):
  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class STBServiceTest(unittest.TestCase):
  def setUp(self):
    self.STATS_FILES_NOEXST = ['testdata/stbservice/notexist%d.json']
    self.old_CONT_MONITOR_FILES = stbservice.CONT_MONITOR_FILES
    self.old_EPG_STATS_FILES = stbservice.EPG_STATS_FILES
    self.old_HDMI_DISP_DEVICE_STATS = stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES
    self.old_HDMI_STATS_FILE = stbservice.HDMI_STATS_FILE
    self.old_PROCNETIGMP = stbservice.PROCNETIGMP
    self.old_PROCNETIGMP6 = stbservice.PROCNETIGMP6
    self.old_PROCNETUDP = stbservice.PROCNETUDP
    self.old_TIMENOW = stbservice.TIMENOW

    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_full%d.json']
    stbservice.EPG_STATS_FILES = ['testdata/stbservice/epgstats.json']
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = [
        'testdata/stbservice/hdmi_dispdev_stats.json',
        'testdata/stbservice/hdmi_dispdev_status.json']
    stbservice.HDMI_STATS_FILE = 'testdata/stbservice/hdmi_stats.json'
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp'
    stbservice.PROCNETIGMP6 = 'testdata/stbservice/igmp6'
    stbservice.PROCNETUDP = 'testdata/stbservice/udp'
    stbservice.TIMENOW = MockTime

  def tearDown(self):
    stbservice.CONT_MONITOR_FILES = self.old_CONT_MONITOR_FILES
    stbservice.EPG_STATS_FILES = self.old_EPG_STATS_FILES
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = self.old_HDMI_DISP_DEVICE_STATS
    stbservice.HDMI_STATS_FILE = self.old_HDMI_STATS_FILE
    stbservice.PROCNETIGMP = self.old_PROCNETIGMP
    stbservice.PROCNETIGMP6 = self.old_PROCNETIGMP6
    stbservice.PROCNETUDP = self.old_PROCNETUDP

  def testValidateExports(self):
    stb = stbservice.STBService()
    stb.ValidateExports()

  def testClientGroups(self):
    stb = stbservice.STBService()
    igmp = stb.Components.FrontEndList['1'].IP.IGMP
    self.assertEqual(len(igmp.ClientGroupList), 12)
    expected = set(['224.0.0.1', '225.0.1.3', '225.0.1.6', '225.0.1.10',
                    '225.0.1.13', '225.0.1.18', '225.0.1.20', '225.0.1.153',
                    '225.0.1.158', 'ff02::1', 'ff02::1:ff30:66af',
                    'ff02::1:ff30:64af'])
    actual = set()
    for i in range(1, 13):
      actual.add(igmp.ClientGroupList[i].GroupAddress)
    self.assertEqual(expected, actual)

  def testClientGroupsStable(self):
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp_stable1'
    stbservice.PROCNETIGMP6 = 'testdata/stbservice/igmp6_stable1'
    stb = stbservice.STBService()
    igmp = stb.Components.FrontEndList['1'].IP.IGMP
    self.assertEqual(len(igmp.ClientGroupList), 5)
    # instances are sorted when possible
    self.assertEqual(igmp.ClientGroupList[1].GroupAddress, '224.0.0.1')
    self.assertEqual(igmp.ClientGroupList[2].GroupAddress, '225.0.1.3')
    self.assertEqual(igmp.ClientGroupList[3].GroupAddress, '225.0.1.4')
    self.assertEqual(igmp.ClientGroupList[4].GroupAddress, '225.0.1.5')
    self.assertEqual(igmp.ClientGroupList[5].GroupAddress, '225.0.1.6')
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp_stable2'
    tr.session.cache.flush()
    self.assertEqual(len(igmp.ClientGroupList), 5)
    # instances retain stable numbering when possible
    self.assertEqual(igmp.ClientGroupList[1].GroupAddress, '224.0.0.1')
    self.assertEqual(igmp.ClientGroupList[2].GroupAddress, '225.0.1.3')
    self.assertEqual(igmp.ClientGroupList[3].GroupAddress, '225.0.1.4')
    self.assertEqual(igmp.ClientGroupList[4].GroupAddress, '225.0.1.7')
    self.assertEqual(igmp.ClientGroupList[5].GroupAddress, '225.0.1.6')
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp_stable3'
    tr.session.cache.flush()
    self.assertEqual(len(igmp.ClientGroupList), 6)
    # instances retain stable numbering when possible
    self.assertEqual(igmp.ClientGroupList[1].GroupAddress, '224.0.0.1')
    self.assertEqual(igmp.ClientGroupList[2].GroupAddress, '225.0.1.3')
    self.assertEqual(igmp.ClientGroupList[3].GroupAddress, '225.0.1.8')
    self.assertEqual(igmp.ClientGroupList[4].GroupAddress, '225.0.1.7')
    self.assertEqual(igmp.ClientGroupList[5].GroupAddress, '225.0.1.6')
    self.assertEqual(igmp.ClientGroupList[6].GroupAddress, '225.0.1.9')

  def checkMPEG2Zero(self, stream):
    self.assertEqual(stream.Total.MPEG2TSStats.TSPacketsReceived, 0)
    self.assertEqual(stream.Total.MPEG2TSStats.PacketDiscontinuityCounter, 0)
    self.assertEqual(stream.Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 0)
    self.assertEqual(stream.Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 0)
    self.assertEqual(
        stream.Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 0)

  def testNonexistentStatsFile(self):
    """Test whether the absence of stats file is handled gracefully."""
    stbservice.CONT_MONITOR_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[1])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[2])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[3])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[4])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[5])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[6])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[7])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[8])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[256])

  def testIncorrectStatsFileFormat(self):
    """Test whether a malformed stats file is handled gracefully."""
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_notjson%d.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[1])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[2])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[3])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[4])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[5])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[6])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[7])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[8])
    self.checkMPEG2Zero(stb.ServiceMonitoring.MainStreamList[256])

  def testIncorrectObjectListIndex(self):
    """Test whether incorrect indexing of the stream object is handled."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    self.assertRaises(KeyError,
                      lambda: stb.ServiceMonitoring.MainStreamList[9])

  def testDynamicUpdate(self):
    """Test whether the object stays consistent when the file is updated."""
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_small%d.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    self.assertEqual(ml[1].Total.MPEG2TSStats.TSPacketsReceived, 400)
    self.assertEqual(ml[2].Total.MPEG2TSStats.TSPacketsReceived, 350)
    self.assertEqual(ml[3].Total.MPEG2TSStats.TSPacketsReceived, 300)
    self.assertEqual(ml[4].Total.MPEG2TSStats.TSPacketsReceived, 0)
    self.assertEqual(ml[5].Total.MPEG2TSStats.TSPacketsReceived, 0)
    self.assertEqual(ml[6].Total.MPEG2TSStats.TSPacketsReceived, 0)
    self.assertEqual(ml[7].Total.MPEG2TSStats.TSPacketsReceived, 0)
    self.assertEqual(ml[8].Total.MPEG2TSStats.TSPacketsReceived, 50)
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_full%d.json']
    tr.session.cache.flush()
    self.assertEqual(ml[1].Total.MPEG2TSStats.TSPacketsReceived, 800)
    self.assertEqual(ml[2].Total.MPEG2TSStats.TSPacketsReceived, 700)
    self.assertEqual(ml[3].Total.MPEG2TSStats.TSPacketsReceived, 600)
    self.assertEqual(ml[4].Total.MPEG2TSStats.TSPacketsReceived, 500)
    self.assertEqual(ml[5].Total.MPEG2TSStats.TSPacketsReceived, 400)
    self.assertEqual(ml[6].Total.MPEG2TSStats.TSPacketsReceived, 300)
    self.assertEqual(ml[7].Total.MPEG2TSStats.TSPacketsReceived, 200)
    self.assertEqual(ml[8].Total.MPEG2TSStats.TSPacketsReceived, 100)

  def testPartialUpdate(self):
    """Test whether a stats file with a subset of objects is deserialized."""
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_p%d.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    self.assertEqual(ml[1].Total.MPEG2TSStats.TSPacketsReceived, 1)
    self.assertEqual(ml[1].Total.MPEG2TSStats.PacketDiscontinuityCounter, 2)
    self.assertEqual(ml[1].Total.TCPStats.PacketsReceived, 3)
    self.assertEqual(ml[1].Total.TCPStats.BytesReceived, 4)
    self.assertEqual(ml[1].Total.TCPStats.PacketsRetransmitted, 5)
    # Dejittering stats not present in file. Check whether the object is init'ed
    self.assertEqual(ml[1].Total.DejitteringStats.EmptyBufferTime, 0)
    self.assertEqual(ml[1].Total.DejitteringStats.Overruns, 0)
    self.assertEqual(ml[1].Total.DejitteringStats.Underruns, 0)

  def testTSStats(self):
    """Test whether transport stream stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    self.assertEqual(ml[1].Total.MPEG2TSStats.TSPacketsReceived, 800)
    self.assertEqual(ml[2].Total.MPEG2TSStats.TSPacketsReceived, 700)
    self.assertEqual(ml[3].Total.MPEG2TSStats.TSPacketsReceived, 600)
    self.assertEqual(ml[4].Total.MPEG2TSStats.TSPacketsReceived, 500)
    self.assertEqual(ml[5].Total.MPEG2TSStats.TSPacketsReceived, 400)
    self.assertEqual(ml[6].Total.MPEG2TSStats.TSPacketsReceived, 300)
    self.assertEqual(ml[7].Total.MPEG2TSStats.TSPacketsReceived, 200)
    self.assertEqual(ml[8].Total.MPEG2TSStats.TSPacketsReceived, 100)
    self.assertEqual(ml[1].Total.MPEG2TSStats.PacketDiscontinuityCounter, 80)
    self.assertEqual(ml[2].Total.MPEG2TSStats.PacketDiscontinuityCounter, 70)
    self.assertEqual(ml[3].Total.MPEG2TSStats.PacketDiscontinuityCounter, 60)
    self.assertEqual(ml[4].Total.MPEG2TSStats.PacketDiscontinuityCounter, 50)
    self.assertEqual(ml[5].Total.MPEG2TSStats.PacketDiscontinuityCounter, 40)
    self.assertEqual(ml[6].Total.MPEG2TSStats.PacketDiscontinuityCounter, 30)
    self.assertEqual(ml[7].Total.MPEG2TSStats.PacketDiscontinuityCounter, 20)
    self.assertEqual(ml[8].Total.MPEG2TSStats.PacketDiscontinuityCounter, 10)
    self.assertEqual(ml[1].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 8000)
    self.assertEqual(ml[2].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 7000)
    self.assertEqual(ml[3].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 6000)
    self.assertEqual(ml[4].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 5000)
    self.assertEqual(ml[5].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 4000)
    self.assertEqual(ml[6].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 3000)
    self.assertEqual(ml[7].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 2000)
    self.assertEqual(ml[8].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropBytes, 1000)
    self.assertEqual(ml[1].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 801)
    self.assertEqual(ml[2].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 701)
    self.assertEqual(ml[3].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 601)
    self.assertEqual(ml[4].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 501)
    self.assertEqual(ml[5].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 401)
    self.assertEqual(ml[6].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 301)
    self.assertEqual(ml[7].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 201)
    self.assertEqual(ml[8].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_DropPackets, 101)
    self.assertEqual(
        ml[1].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 8)
    self.assertEqual(
        ml[2].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 7)
    self.assertEqual(
        ml[3].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 6)
    self.assertEqual(
        ml[4].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 5)
    self.assertEqual(
        ml[5].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 4)
    self.assertEqual(
        ml[6].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 3)
    self.assertEqual(
        ml[7].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 2)
    self.assertEqual(
        ml[8].Total.MPEG2TSStats.X_CATAWAMPUS_ORG_PacketErrorCount, 1)

  def testDejitteringStats(self):
    """Test whether Dejittering stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    self.assertEqual(ml[1].Total.DejitteringStats.EmptyBufferTime, 47)
    self.assertEqual(ml[2].Total.DejitteringStats.EmptyBufferTime, 41)
    self.assertEqual(ml[3].Total.DejitteringStats.EmptyBufferTime, 31)
    self.assertEqual(ml[4].Total.DejitteringStats.EmptyBufferTime, 23)
    self.assertEqual(ml[5].Total.DejitteringStats.EmptyBufferTime, 17)
    self.assertEqual(ml[6].Total.DejitteringStats.EmptyBufferTime, 11)
    self.assertEqual(ml[7].Total.DejitteringStats.EmptyBufferTime, 5)
    self.assertEqual(ml[8].Total.DejitteringStats.EmptyBufferTime, 1)
    self.assertEqual(ml[1].Total.DejitteringStats.Overruns, 8)
    self.assertEqual(ml[2].Total.DejitteringStats.Overruns, 7)
    self.assertEqual(ml[3].Total.DejitteringStats.Overruns, 6)
    self.assertEqual(ml[4].Total.DejitteringStats.Overruns, 5)
    self.assertEqual(ml[5].Total.DejitteringStats.Overruns, 4)
    self.assertEqual(ml[6].Total.DejitteringStats.Overruns, 3)
    self.assertEqual(ml[7].Total.DejitteringStats.Overruns, 2)
    self.assertEqual(ml[8].Total.DejitteringStats.Overruns, 1)
    self.assertEqual(ml[1].Total.DejitteringStats.Underruns, 11)
    self.assertEqual(ml[2].Total.DejitteringStats.Underruns, 12)
    self.assertEqual(ml[3].Total.DejitteringStats.Underruns, 13)
    self.assertEqual(ml[4].Total.DejitteringStats.Underruns, 14)
    self.assertEqual(ml[5].Total.DejitteringStats.Underruns, 15)
    self.assertEqual(ml[6].Total.DejitteringStats.Underruns, 16)
    self.assertEqual(ml[7].Total.DejitteringStats.Underruns, 17)
    self.assertEqual(ml[8].Total.DejitteringStats.Underruns, 18)

  def testTCPStatsAll(self):
    """Test whether all TCP stats are deserialized."""
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_tcp%d.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    tcp = stb.ServiceMonitoring.MainStreamList[1].Total.TCPStats
    self.assertEqual(tcp.BytesReceived, 1)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_BytesSent, 2)
    self.assertEqual(tcp.PacketsReceived, 3)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_Cwnd, 5)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_SlowStartThreshold, 6)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_Unacked, 7)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_Sacked, 8)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_Lost, 9)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_Rtt, 10)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_RttVariance, 11)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_ReceiveRTT, 12)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_ReceiveSpace, 13)
    self.assertEqual(tcp.X_CATAWAMPUS_ORG_RetransmitTimeout, 14)
    self.assertEqual(tcp.PacketsRetransmitted, 15)

  def testTCPStatsMultiple(self):
    """Test whether TCP stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    self.assertEqual(ml[1].Total.TCPStats.PacketsReceived, 8000)
    self.assertEqual(ml[1].Total.TCPStats.BytesReceived, 2048000)
    self.assertEqual(ml[1].Total.TCPStats.PacketsRetransmitted, 9)
    self.assertEqual(ml[2].Total.TCPStats.PacketsReceived, 7000)
    self.assertEqual(ml[2].Total.TCPStats.BytesReceived, 1792000)
    self.assertEqual(ml[2].Total.TCPStats.PacketsRetransmitted, 6)
    self.assertEqual(ml[3].Total.TCPStats.PacketsReceived, 6000)
    self.assertEqual(ml[3].Total.TCPStats.BytesReceived, 1536000)
    self.assertEqual(ml[3].Total.TCPStats.PacketsRetransmitted, 7)
    self.assertEqual(ml[4].Total.TCPStats.PacketsReceived, 5000)
    self.assertEqual(ml[4].Total.TCPStats.BytesReceived, 1280000)
    self.assertEqual(ml[4].Total.TCPStats.PacketsRetransmitted, 4)
    self.assertEqual(ml[5].Total.TCPStats.PacketsReceived, 4000)
    self.assertEqual(ml[5].Total.TCPStats.BytesReceived, 1024000)
    self.assertEqual(ml[5].Total.TCPStats.PacketsRetransmitted, 5)
    self.assertEqual(ml[6].Total.TCPStats.PacketsReceived, 3000)
    self.assertEqual(ml[6].Total.TCPStats.BytesReceived, 768000)
    self.assertEqual(ml[6].Total.TCPStats.PacketsRetransmitted, 2)
    self.assertEqual(ml[7].Total.TCPStats.PacketsReceived, 2000)
    self.assertEqual(ml[7].Total.TCPStats.BytesReceived, 512000)
    self.assertEqual(ml[7].Total.TCPStats.PacketsRetransmitted, 3)
    self.assertEqual(ml[8].Total.TCPStats.PacketsReceived, 1000)
    self.assertEqual(ml[8].Total.TCPStats.BytesReceived, 256000)
    self.assertEqual(ml[8].Total.TCPStats.PacketsRetransmitted, 1)

  def testMulticastStats(self):
    """Test whether multicast stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    expected_mc = set(['225.0.0.1:1', '225.0.0.2:2', '225.0.0.3:3',
                       '225.0.0.4:4', '225.0.0.5:5', '225.0.0.6:6',
                       '225.0.0.7:7', '225.0.0.8:8'])
    expected_bps = {
        '225.0.0.1:1': 1000000, '225.0.0.2:2': 2000000, '225.0.0.3:3': 3000000,
        '225.0.0.4:4': 4000000, '225.0.0.5:5': 5000000, '225.0.0.6:6': 6000000,
        '225.0.0.7:7': 7000000, '225.0.0.8:8': 8000000}
    expected_stall = {
        '225.0.0.1:1': 1, '225.0.0.2:2': 2, '225.0.0.3:3': 3, '225.0.0.4:4': 4,
        '225.0.0.5:5': 5, '225.0.0.6:6': 6, '225.0.0.7:7': 7, '225.0.0.8:8': 8}
    expected_startup = {
        '225.0.0.1:1': 9, '225.0.0.2:2': 10, '225.0.0.3:3': 11,
        '225.0.0.4:4': 12, '225.0.0.5:5': 13, '225.0.0.6:6': 14,
        '225.0.0.7:7': 15, '225.0.0.8:8': 16}
    expected_rxq = {
        '225.0.0.1:1': 0xa77, '225.0.0.2:2': 0, '225.0.0.3:3': 0,
        '225.0.0.4:4': 0, '225.0.0.5:5': 0, '225.0.0.6:6': 0, '225.0.0.7:7': 0,
        '225.0.0.8:8': 0}
    expected_drops = {
        '225.0.0.1:1': 1000, '225.0.0.2:2': 0, '225.0.0.3:3': 0,
        '225.0.0.4:4': 0, '225.0.0.5:5': 0, '225.0.0.6:6': 0, '225.0.0.7:7': 0,
        '225.0.0.8:8': 0}
    expected_missed = {
        '225.0.0.1:1': 10, '225.0.0.2:2': 20, '225.0.0.3:3': 30,
        '225.0.0.4:4': 40, '225.0.0.5:5': 50, '225.0.0.6:6': 60,
        '225.0.0.7:7': 70, '225.0.0.8:8': 80}

    actual_mc = set()
    for v in stb.ServiceMonitoring.MainStreamList.values():
      mcstats = v.Total.X_CATAWAMPUS_ORG_MulticastStats
      group = mcstats.MulticastGroup
      if group:
        actual_mc.add(group)
        self.assertEqual(expected_bps[group], mcstats.BPS)
        self.assertEqual(expected_stall[group], mcstats.StallTime)
        self.assertEqual(expected_rxq[group], mcstats.UdpRxQueue)
        self.assertEqual(expected_drops[group], mcstats.UdpDrops)
        self.assertEqual(expected_startup[group], mcstats.StartupLatency)
        self.assertEqual(expected_missed[group], mcstats.MissedSchedule)
    self.assertEqual(expected_mc, actual_mc)

  def testNonexistentHDMIStatsFile(self):
    """Test whether the absence of HDMI stats file is handled gracefully."""
    stbservice.HDMI_STATS_FILE = self.STATS_FILES_NOEXST[0]
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '')
      self.assertEqual(v.DisplayDevice.Status, 'None')
      self.assertEqual(v.DisplayDevice.Name, '')
      self.assertEqual(v.DisplayDevice.EEDID, '')
      self.assertEqual(len(v.DisplayDevice.SupportedResolutions), 0)
      self.assertEqual(v.DisplayDevice.PreferredResolution, '')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_HDCPAuthFailureCnt, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, '')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 1990)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_LastUpdateTimestamp,
                       '0001-01-01T00:00:00Z')

  def testDecoderStats(self):
    """Test whether Decoder stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 9)
    ml = stb.ServiceMonitoring.MainStreamList
    for i in range(1, 7):
      stats = ml[i].Total.X_CATAWAMPUS_ORG_DecoderStats
      self.assertEqual(stats.VideoBytesDecoded, 13)
      self.assertEqual(stats.DecodeDrops, 7)
      self.assertEqual(stats.VideoDecodeErrors, 5)
      self.assertEqual(stats.DecodeOverflows, 6)
      self.assertEqual(stats.DecodedPictures, 4)
      self.assertEqual(stats.DisplayErrors, 9)
      self.assertEqual(stats.DisplayDrops, 10)
      self.assertEqual(stats.DisplayUnderflows, 11)
      self.assertEqual(stats.DisplayedPictures, 8)
      self.assertEqual(stats.ReceivedPictures, 3)
      self.assertEqual(stats.VideoWatchdogs, 12)
      self.assertEqual(stats.VideoPtsStcDifference, 14)
      self.assertEqual(stats.AudioDecodedFrames, 15)
      self.assertEqual(stats.AudioDecodeErrors, 16)
      self.assertEqual(stats.AudioDummyFrames, 17)
      self.assertEqual(stats.AudioFifoOverflows, 18)
      self.assertEqual(stats.AudioFifoUnderflows, 19)
      self.assertEqual(stats.AudioWatchdogs, 20)
      self.assertEqual(stats.AudioBytesDecoded, 21)
      self.assertEqual(stats.AudioPtsStcDifference, 22)
      self.assertEqual(stats.VideoFifoDepth, 30)
      self.assertEqual(stats.VideoDisplayQueueDepth, 31)
      self.assertEqual(stats.VideoCabacQueueDepth, 32)
      self.assertEqual(stats.VideoEnhancementFifoDepth, 33)
      self.assertEqual(stats.VideoPts, 34)
      self.assertEqual(stats.AudioFifoDepth, 35)
      self.assertEqual(stats.AudioQueuedFrames, 36)
      self.assertEqual(stats.AudioPts, 37)

    for i in range(7, 9):
      stats = ml[i].Total.X_CATAWAMPUS_ORG_DecoderStats
      self.assertEqual(stats.VideoBytesDecoded, 0)
      self.assertEqual(stats.DecodeDrops, 0)
      self.assertEqual(stats.VideoDecodeErrors, 0)
      self.assertEqual(stats.DecodeOverflows, 0)
      self.assertEqual(stats.DecodedPictures, 0)
      self.assertEqual(stats.DisplayErrors, 0)
      self.assertEqual(stats.DisplayDrops, 0)
      self.assertEqual(stats.DisplayUnderflows, 0)
      self.assertEqual(stats.DisplayedPictures, 0)
      self.assertEqual(stats.ReceivedPictures, 0)
      self.assertEqual(stats.VideoWatchdogs, 0)
      self.assertEqual(stats.VideoPtsStcDifference, 0)
      self.assertEqual(stats.AudioDecodedFrames, 0)
      self.assertEqual(stats.AudioDecodeErrors, 0)
      self.assertEqual(stats.AudioDummyFrames, 0)
      self.assertEqual(stats.AudioFifoOverflows, 0)
      self.assertEqual(stats.AudioFifoUnderflows, 0)
      self.assertEqual(stats.AudioWatchdogs, 0)
      self.assertEqual(stats.AudioBytesDecoded, 0)
      self.assertEqual(stats.AudioPtsStcDifference, 0)

  def testHDMIStatsAll(self):
    """Test deserialization of all HDMI stats parameters."""
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.Status, 'Present')
      self.assertEqual(v.DisplayDevice.Name, 'X213W')
      self.assertEqual(v.DisplayDevice.EEDID, ('00ffffffffffff000472330088b4808'
                                               '008120103802f1e78eade95a3544c99'
                                               '260f5054bfef90a940714f814001019'
                                               '500950f9040010121399030621a2740'
                                               '68b03600da2811000019000000fd003'
                                               '84d1f5411000a202020202020000000'
                                               'ff004c43473043303233343031300a0'
                                               '00000fc0058323133570a2020202020'
                                               '202000d9'))
      self.assertEqual(v.DisplayDevice.SupportedResolutions, ('640x480 @ 51Hz, '
                                                              '640x480 @ 52Hz, '
                                                              '640x480 @ 55Hz'))
      self.assertEqual(v.DisplayDevice.PreferredResolution, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)

      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_EDIDExtensions,
                       v.DisplayDevice.EEDID + ', ' + v.DisplayDevice.EEDID)

      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 3)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 9)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_HDCPAuthFailureCnt, 5)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, 'ACR')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 51)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 2008)

  def testIncorrectHDMIStatsFile(self):
    """Test deserialization when a subset of stats files are invalid."""
    stbservice.HDMI_STATS_FILE = stbservice.PROCNETIGMP
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '')
      self.assertEqual(v.DisplayDevice.Name, 'X213W')

  def testPartialHDMIStatsFiles(self):
    """Test deserialization when a subset of files are not present."""
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = [
        'testdata/stbservice/hdmi_dispdev_status*.json',
        'testdata/stbservice/nosuchfile*.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.Status, 'Present')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 3)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 9)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_HDCPAuthFailureCnt, 5)
      self.assertEqual(v.DisplayDevice.Name, '')
      self.assertEqual(v.DisplayDevice.EEDID, '')
      self.assertEqual(len(v.DisplayDevice.SupportedResolutions), 0)
      self.assertEqual(v.DisplayDevice.PreferredResolution, '')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, '')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 1990)

  def testEPGStatsNoFile(self):
    """Test whether EPG stats are deserialized properly when not file backed."""
    stbservice.EPG_STATS_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 0)
    self.assertEqual(epgStats.EPGErrors, 0)
    self.assertEqual(epgStats.LastReceivedTime, '0001-01-01T00:00:00Z')
    self.assertEqual(epgStats.EPGExpireTime, '0001-01-01T00:00:00Z')

  def testEPGStatsIncorrectFileFormat(self):
    """Test whether EPG stats are handled properly for a bad file."""
    stbservice.EPG_STATS_FILES = [stbservice.PROCNETIGMP]
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 0)
    self.assertEqual(epgStats.EPGErrors, 0)
    self.assertEqual(epgStats.LastReceivedTime, '0001-01-01T00:00:00Z')
    self.assertEqual(epgStats.EPGExpireTime, '0001-01-01T00:00:00Z')
    self.assertEqual(epgStats.NumChannels, 0)
    self.assertEqual(epgStats.NumEnabledChannels, 0)

  def testEPGStatsAll(self):
    """Test whether EPG stats are deserialized properly."""
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 1002)
    self.assertEqual(epgStats.EPGErrors, 2)
    self.assertEqual(epgStats.LastReceivedTime, '2012-07-25T01:50:37Z')
    self.assertEqual(epgStats.EPGExpireTime, '2012-07-30T01:50:37Z')
    self.assertEqual(epgStats.NumChannels, 20)
    self.assertEqual(epgStats.NumEnabledChannels, 21)

  def testStallAlarm(self):
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_small%d.json']
    ioloop = MockIoloop()
    stb = stbservice.STBService(ioloop=ioloop)
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '0001-01-01T00:00:00Z')
    stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmValue = 1
    # small1 is not exceeding the AlarmValue
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '0001-01-01T00:00:00Z')
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_full%d.json']
    tr.session.cache.flush()
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '2013-01-11T10:00:00Z')
    self.assertTrue(ioloop.callback is not None)
    # Alarm should stay asserted even when stalltime drops below threshold.
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_small%d.json']
    tr.session.cache.flush()
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '2013-01-11T10:00:00Z')
    # Explicitly clear
    stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime = 0
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '0001-01-01T00:00:00Z')

  def testStallAlarmReset(self):
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_full%d.json']
    ioloop = MockIoloop()
    stb = stbservice.STBService(ioloop=ioloop)
    stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmValue = 1
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '2013-01-11T10:00:00Z')
    self.assertTrue(ioloop.callback is not None)
    # Stalltime drops back below threshold
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_small%d.json']
    tr.session.cache.flush()
    # Simulate timeout callback
    ioloop.callback()
    self.assertEqual(stb.ServiceMonitoring.X_CATAWAMPUS_ORG_StallAlarmTime,
                     '0001-01-01T00:00:00Z')

  def testAlanCoxIP(self):
    saddr = socket.inet_pton(socket.AF_INET, '1.2.3.4')
    num = struct.unpack('=L', saddr)[0]
    snum = hex(num)[2:]  # 1020304 on BE host, 4030201 on LE.
    self.assertEqual(stbservice.UnpackAlanCoxIP(snum), '1.2.3.4')


if __name__ == '__main__':
  unittest.main()
