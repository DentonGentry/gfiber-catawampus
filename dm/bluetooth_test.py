#!/usr/bin/python
# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Unit tests for bluetooth.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import time
import google3
from tr.wvtest import unittest
import bluetooth
import tr.handle
import tr.helpers
import tr.mainloop


class iBeaconTest(unittest.TestCase):

  def setUp(self):
    super(iBeaconTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.outfile = os.path.join(self.tmpdir, 'out')
    self.old_IBEACONCMD = bluetooth.IBEACONCMD
    bluetooth.IBEACONCMD = ['testdata/bluetooth/ibeacon', self.outfile]
    self.old_EDDYSTONECMD = bluetooth.EDDYSTONECMD
    bluetooth.EDDYSTONECMD = ['testdata/bluetooth/eddystone', self.outfile]
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    super(iBeaconTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    bluetooth.IBEACONCMD = self.old_IBEACONCMD
    bluetooth.EDDYSTONECMD = self.old_EDDYSTONECMD
    tr.helpers.Unlink(self.outfile)

  def testValidateExports(self):
    b = bluetooth.Bluetooth()
    tr.handle.ValidateExports(b)

  def testIBeacon(self):
    i = bluetooth.iBeacon()
    i.UUID = '95b224d2-8e27-45d5-80c9-69b59df330e5'
    i.Major = 1
    i.Minor = 2
    i.TxPower = 3
    i.Enable = True
    self.loop.RunOnce()
    for _ in range(1, 5):
      # give the script time to run
      if not os.path.exists(self.outfile):
        time.sleep(0.2)
    self.assertTrue(os.path.exists(self.outfile))
    buf = open(self.outfile).read()
    self.assertTrue('-u 95b224d2-8e27-45d5-80c9-69b59df330e5' in buf)
    self.assertTrue('-m 1' in buf)
    self.assertTrue('-n 2' in buf)
    self.assertTrue('-t 3' in buf)
    self.assertFalse('-d' in buf)
    os.unlink(self.outfile)

    i.Enable = False
    self.loop.RunOnce()
    for _ in range(1, 5):
      if not os.path.exists(self.outfile):
        time.sleep(0.2)
    self.assertTrue(os.path.exists(self.outfile))
    buf = open(self.outfile).read()
    self.assertTrue('-d' in buf)

  def testEddystone(self):
    b = bluetooth.Eddystone()
    b.Namespace = '00112233445566778899'
    b.Instance = 'aabbccddeeff'
    b.TxPower = 3
    b.Enable = True
    self.loop.RunOnce()
    for _ in range(1, 5):
      # give the script time to run
      if not os.path.exists(self.outfile):
        time.sleep(0.2)
    self.assertTrue(os.path.exists(self.outfile))
    buf = open(self.outfile).read()
    self.assertTrue('-n 00112233445566778899' in buf)
    self.assertTrue('-i aabbccddeeff' in buf)
    self.assertTrue('-t 3' in buf)
    self.assertFalse('-d' in buf)
    os.unlink(self.outfile)

    b.Enable = False
    self.loop.RunOnce()
    for _ in range(1, 5):
      if not os.path.exists(self.outfile):
        time.sleep(0.2)
    self.assertTrue(os.path.exists(self.outfile))
    buf = open(self.outfile).read()
    self.assertTrue('-d' in buf)


if __name__ == '__main__':
  unittest.main()
