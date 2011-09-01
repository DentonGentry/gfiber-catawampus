#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Tests for auto-generated tr???_*.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import core
import os
import sys
import tr098_v1_2 as tr098
import unittest


class MyModel(tr098.InternetGatewayDevice_v1_4):
    def __init__(self):
        tr098.InternetGatewayDevice_v1_4.__init__(self)
        self.InternetGatewayDevice = core.TODO()
        u = self.UDPEchoConfig = self.UDPEchoConfig()
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
        self.UploadDiagnostics = core.TODO()
        self.Capabilities = core.TODO()
        self.DownloadDiagnostics = core.TODO()


class StdTest(unittest.TestCase):
    def testStd(self):
        o = MyModel()
        o.ValidateExports()
        print core.Dump(o)


if __name__ == '__main__':
  unittest.main()
