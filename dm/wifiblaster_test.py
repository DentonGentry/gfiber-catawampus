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

"""Tests for wifiblaster data model."""

__author__ = 'mikemu@google.com (Mike Mu)'

import os
import shutil
import tempfile
import unittest
import google3
import tr.handle
import tr.mainloop
import wifiblaster


class WifiblasterTest(unittest.TestCase):

  def setUp(self):
    self.old_basedir = wifiblaster.BASEDIR[0]
    self.old_duration_file = wifiblaster.DURATION_FILE[0]
    self.old_enable_file = wifiblaster.ENABLE_FILE[0]
    self.old_fraction_file = wifiblaster.FRACTION_FILE[0]
    self.old_interval_file = wifiblaster.INTERVAL_FILE[0]
    self.old_measureall_file = wifiblaster.MEASUREALL_FILE[0]
    self.old_size_file = wifiblaster.SIZE_FILE[0]

    self.basedir = tempfile.mkdtemp()
    self.duration_file = os.path.join(self.basedir, 'wifiblaster.duration')
    self.enable_file = os.path.join(self.basedir, 'wifiblaster.enable')
    self.fraction_file = os.path.join(self.basedir, 'wifiblaster.fraction')
    self.interval_file = os.path.join(self.basedir, 'wifiblaster.interval')
    self.measureall_file = os.path.join(self.basedir, 'wifiblaster.measureall')
    self.size_file = os.path.join(self.basedir, 'wifiblaster.size')

    wifiblaster.BASEDIR[0] = self.basedir
    wifiblaster.DURATION_FILE[0] = self.duration_file
    wifiblaster.ENABLE_FILE[0] = self.enable_file
    wifiblaster.FRACTION_FILE[0] = self.fraction_file
    wifiblaster.INTERVAL_FILE[0] = self.interval_file
    wifiblaster.MEASUREALL_FILE[0] = self.measureall_file
    wifiblaster.SIZE_FILE[0] = self.size_file

    self.wifiblaster = wifiblaster.Wifiblaster()
    self.loop = tr.mainloop.MainLoop()

  def testFiles(self):
    self.wifiblaster.Duration = .5
    self.wifiblaster.Enable = True
    self.wifiblaster.Fraction = 20
    self.wifiblaster.Interval = .5
    self.wifiblaster.MeasureAll = 1000
    self.wifiblaster.Size = 100
    self.loop.RunOnce()
    with open(self.duration_file) as f:
      self.assertEquals(float(f.read()), .5)
    with open(self.enable_file) as f:
      self.assertIn(str(f.read().rstrip().lower()), ('true', '1'))
    with open(self.fraction_file) as f:
      self.assertEquals(int(f.read()), 20)
    with open(self.interval_file) as f:
      self.assertEquals(float(f.read()), .5)
    with open(self.measureall_file) as f:
      self.assertEquals(float(f.read()), 1000)
    with open(self.size_file) as f:
      self.assertEquals(int(f.read()), 100)

  def tearDown(self):
    shutil.rmtree(self.basedir)
    wifiblaster.BASEDIR[0] = self.old_basedir
    wifiblaster.DURATION_FILE[0] = self.old_duration_file
    wifiblaster.ENABLE_FILE[0] = self.old_enable_file
    wifiblaster.FRACTION_FILE[0] = self.old_fraction_file
    wifiblaster.INTERVAL_FILE[0] = self.old_interval_file
    wifiblaster.MEASUREALL_FILE[0] = self.old_measureall_file
    wifiblaster.SIZE_FILE[0] = self.old_size_file


if __name__ == '__main__':
  unittest.main()
