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
# pylint:disable=invalid-name

"""Unit tests for miniupnp.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
from tr.wvtest import unittest
import miniupnp
import tr.handle
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

  def tearDown(self):
    super(MiniUPnPTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    miniupnp.RESTARTCMD = self.old_RESTARTCMD
    miniupnp.UPNPFILE = self.old_UPNPFILE

  def testValidateExports(self):
    upnp = miniupnp.UPnP()
    tr.handle.ValidateExports(upnp)

  def testEnable(self):
    upnp = miniupnp.UPnP()

    # not fully enabled yet
    upnp.Device.Enable = True
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertFalse(os.path.exists(self.restartfile))

    # enable for realz
    upnp.Device.UPnPIGD = True
    self.loop.RunOnce(timeout=1)
    self.assertTrue(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)

    # disable for realz
    upnp.Device.Enable = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertTrue(os.path.exists(self.restartfile))
    tr.helpers.Unlink(self.restartfile)

    # already disabled, no action should be taken
    upnp.Device.UPnPIGD = False
    self.loop.RunOnce(timeout=1)
    self.assertFalse(os.path.exists(miniupnp.UPNPFILE))
    self.assertFalse(os.path.exists(self.restartfile))


if __name__ == '__main__':
  unittest.main()
