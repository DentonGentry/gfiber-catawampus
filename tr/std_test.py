#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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
"""Tests for auto-generated tr???_*.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

from wvtest import unittest
import core
import handle
import tr098_v1_2 as tr098

BASE098IGD = tr098.InternetGatewayDevice_v1_4.InternetGatewayDevice


class MyModel(BASE098IGD):

  def __init__(self):
    BASE098IGD.__init__(self)
    self.InternetGatewayDevice = core.TODO()
    u = self.UDPEchoConfig = core.Extensible(self.UDPEchoConfig)()
    u.BytesReceived = 0
    u.Enable = True
    u.PacketsReceived = 0
    u.TimeFirstPacketReceived = 0
    u.EchoPlusEnabled = False
    u.UDPPort = 0
    u.EchoPlusSupported = False
    u.Interface = ''
    u.PacketsResponded = ''
    u.SourceIPAddress = '1.2.3.4'
    u.TimeLastPacketReceived = 0
    u.BytesResponded = 0
    self.LANDeviceList = {}
    self.WANDeviceList = {}
    self.LANDeviceNumberOfEntries = 0
    self.WANDeviceNumberOfEntries = 0
    self.DeviceSummary = core.TODO()
    self.TraceRouteDiagnostics = core.TODO()
    self.Layer2Bridging = core.TODO()
    self.ManagementServer = core.TODO()
    self.DeviceInfo = core.TODO()
    self.IPPingDiagnostics = core.TODO()
    self.DeviceConfig = core.TODO()
    self.Services = core.TODO()
    self.Layer3Forwarding = core.TODO()
    self.LANConfigSecurity = core.TODO()
    self.CaptivePortal = core.TODO()
    self.Time = core.TODO()
    self.QueueManagement = core.TODO()
    self.LANInterfaces = core.TODO()
    self.UserInterface = core.TODO()
    self.UploadDiagnostics = core.TODO()
    self.Capabilities = core.TODO()
    self.DownloadDiagnostics = core.TODO()


class StdTest(unittest.TestCase):

  def testStd(self):
    o = MyModel()
    handle.Handle(o).ValidateExports()
    print handle.Dump(o)


if __name__ == '__main__':
  unittest.main()
