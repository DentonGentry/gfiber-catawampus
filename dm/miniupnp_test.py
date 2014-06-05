#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Unit tests for miniupnp.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import miniupnp
import tr.helpers
import tr.mainloop


class MiniUPnPTest(unittest.TestCase):
  def setUp(self):
    super(MiniUPnPTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.old_UPNPFILE = miniupnp.UPNPFILE
    miniupnp.UPNPFILE = os.path.join(self.tmpdir, 'upnpfile')
    self.loop = tr.mainloop.MainLoop()
    self.old_RESTARTCMD = miniupnp.RESTARTCMD
    self.restartfile = os.path.join(self.tmpdir, 'restarted')
    miniupnp.RESTARTCMD = ['testdata/miniupnp/restart', self.restartfile]
    self.old_POLL_CMD = miniupnp.POLL_CMD
    miniupnp.POLL_CMD = ['testdata/miniupnp/ssdp_poll']

  def tearDown(self):
    super(MiniUPnPTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    miniupnp.RESTARTCMD = self.old_RESTARTCMD
    miniupnp.UPNPFILE = self.old_UPNPFILE
    miniupnp.POLL_CMD = self.old_POLL_CMD

  def testValidateExports(self):
    upnp = miniupnp.UPnP()
    upnp.ValidateExports()

  def testEnable(self):
    upnp = miniupnp.UPnP()
    upnp.Device.Enable = True
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)
    upnp.Device.UPnPIGD = True
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)
    upnp.Device.Enable = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)
    upnp.Device.UPnPIGD = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)

  def testSsdpClientInfo(self):
    ssdp = miniupnp.GetSsdpClientInfo()
    self.assertEqual(len(ssdp), 3)
    found = 0
    for (key, value) in ssdp.iteritems():
      if key == '192.168.3.30':
        found |= 1
        self.assertEqual(value, 'HDHomeRun/1.0 UPnP/1.0')
      if key == '192.168.3.31':
        found |= 2
        self.assertEqual(value, 'NT/5.0 Upnp/1.0')
      if key == '192.168.3.32':
        found |= 4
        self.assertEqual(value, 'Windows-Vista/6.0 UPnP/1.0')
    self.assertEqual(found, 7)

  def testSsdpClientInfoMalformed(self):
    miniupnp.POLL_CMD = ['testdata/miniupnp/ssdp_poll_invalid']
    ssdp = miniupnp.GetSsdpClientInfo()
    self.assertEqual(len(ssdp), 0)


if __name__ == '__main__':
  unittest.main()
