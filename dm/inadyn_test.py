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

"""Unit tests for inadyn.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
from tr.wvtest import unittest
import inadyn
import tr.handle
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
    tr.handle.ValidateExports(n)
    s = n.Service()
    tr.handle.ValidateExports(s)

  def testWriteConfigSimple(self):
    n = inadyn.Inadyn()
    h = tr.handle.Handle(n)
    (idx, s) = h.AddExportObject('Service', '1')
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
    expected = ['system name@example.com\n',
                'dyndns_server_url http://example.com/\n',
                'username username\n', 'password password\n',
                'update_period_sec 600\n', 'alias mydomain.com\n',
                'verbose 1\n']
    for e in expected:
      self.assertTrue(e in lines)
      lines.remove(e)
    self.assertEqual(0, len(lines))
    self.assertTrue(os.path.exists(self.restartfile))

  def testStatus(self):
    n = inadyn.Inadyn()
    h = tr.handle.Handle(n)
    (_, s) = h.AddExportObject('Service', '1')
    self.assertEqual(s.Status, 'Disabled')
    s.Enable = True
    self.assertTrue('Misconfigured' in s.Status)
    s.ServiceName = 'name@example.com'
    self.assertTrue('Misconfigured' in s.Status)
    s.Domain = 'mydomain.com'
    self.assertTrue('Enabled' in s.Status)


if __name__ == '__main__':
  unittest.main()
