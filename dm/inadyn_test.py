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

"""Unit tests for inadyn.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
from tr.wvtest import unittest
import inadyn
import tr.mainloop


class InadynTest(unittest.TestCase):

  def setUp(self):
    super(InadynTest, self).setUp()
    self.tmpdir = tempfile.mkdtemp()
    self.loop = tr.mainloop.MainLoop()
    self.old_OUTPUTDIR = inadyn.OUTPUTDIR
    inadyn.OUTPUTDIR = self.tmpdir
    self.old_RESTARTCMD = inadyn.RESTARTCMD
    self.restartfile = os.path.join(self.tmpdir, 'restarted')
    inadyn.RESTARTCMD = ['testdata/inadyn/restart', self.restartfile]

  def tearDown(self):
    super(InadynTest, self).tearDown()
    shutil.rmtree(self.tmpdir)
    inadyn.OUTPUTDIR = self.old_OUTPUTDIR
    inadyn.RESTARTCMD = self.old_RESTARTCMD

  def testValidateExports(self):
    n = inadyn.Inadyn()
    n.ValidateExports()
    s = n.Service()
    s.ValidateExports()

  def testWriteConfigSimple(self):
    n = inadyn.Inadyn()
    (idx, s) = n.AddExportObject('Service', '1')
    s.Domain = 'mydomain.com'
    s.Username = 'username'
    s.Password = 'password'
    s.UpdateFrequency = 10
    s.ServiceName = 'name@example.com'
    s.ServiceURL = 'http://example.com/'
    s.Enable = True
    self.assertFalse(os.path.exists(self.restartfile))
    self.loop.RunOnce(timeout=1)
    filename = os.path.join(self.tmpdir, 'inadyn.' + idx + '.conf')
    self.assertTrue(os.stat(filename))
    lines = open(filename).readlines()
    self.assertEqual(len(lines), 7)
    self.assertTrue('system name@example.com\n' in lines)
    self.assertTrue('dyndns_server_url http://example.com/\n' in lines)
    self.assertTrue('username username\n' in lines)
    self.assertTrue('password password\n' in lines)
    self.assertTrue('update_period_sec 600\n' in lines)
    self.assertTrue('alias mydomain.com\n' in lines)
    self.assertTrue('verbose 1\n' in lines)
    self.assertTrue(os.path.exists(self.restartfile))

  def testStatus(self):
    n = inadyn.Inadyn()
    (_, s) = n.AddExportObject('Service', '1')
    self.assertEqual(s.Status, 'Disabled')
    s.Enable = True
    self.assertTrue('Misconfigured' in s.Status)
    s.ServiceName = 'name@example.com'
    self.assertTrue('Misconfigured' in s.Status)
    s.Domain = 'mydomain.com'
    self.assertTrue('Enabled' in s.Status)


if __name__ == '__main__':
  unittest.main()
