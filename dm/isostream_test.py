#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Unit tests for Isostream implementation."""

import datetime
import itertools
import os
import shutil
import tempfile
import time
import google3

import dm_root
from dm_root_test import MockTr98
from dm_root_test import MockTr181
from dm_root_test import MockManagement
from dm_root_test import MockDevice

# since we import dm_root, we need to import isostream at its fully
# qualified path in order to prevent loading the module twice.
import dm.isostream
import tr.handle
import tr.helpers
import tr.mainloop
from tr.wvtest import unittest


class IsostreamTest(unittest.TestCase):
  """Tests for isostream.py."""

  def setUp(self):
    self.readyfile = 'isos.out.%d.ready' % os.getpid()
    self.logfile = 'isos.out.%d.tmp' % os.getpid()
    tr.helpers.Unlink(self.logfile)
    tr.helpers.Unlink(self.readyfile)

    self.old_basedir = dm.isostream.BASEDIR[0]
    self.old_consensus_key_file = dm.isostream.CONSENSUS_KEY_FILE[0]
    self.basedir = tempfile.mkdtemp()
    self.consensus_key_file = os.path.join(self.basedir, 'consensus_key')
    dm.isostream.BASEDIR[0] = self.basedir
    dm.isostream.CONSENSUS_KEY_FILE[0] = self.consensus_key_file

    tr.helpers.WriteFileAtomic(dm.isostream.CONSENSUS_KEY_FILE[0],
                               '1CatawampusRocks')
    self.oldpath = os.environ['PATH']
    os.environ['PATH'] = '%s/testdata/isostream:%s' % (os.getcwd(),
                                                       os.environ['PATH'])
    self.loop = tr.mainloop.MainLoop()

  def tearDown(self):
    os.environ['PATH'] = self.oldpath
    tr.helpers.Unlink(self.logfile)
    tr.helpers.Unlink(self.readyfile)
    shutil.rmtree(self.basedir)
    dm.isostream.BASEDIR[0] = self.old_basedir
    dm.isostream.CONSENSUS_KEY_FILE[0] = self.old_consensus_key_file

  def _WaitReady(self):
    for _ in xrange(1000):
      if os.path.exists(self.readyfile):
        return
      time.sleep(0.01)
    raise Exception('readyfile %r not created after a long time'
                    % self.readyfile)

  def _Iter(self, expect):
    tr.helpers.Unlink(self.readyfile)
    self.loop.RunOnce()
    self._WaitReady()
    self.assertEqual(open(self.logfile).read(), expect)
    tr.helpers.Unlink(self.logfile)

  def testValidate(self):
    tr.handle.ValidateExports(dm.isostream.Isostream())

  def testServer(self):
    isos = dm.isostream.Isostream()
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    isos.ServerEnable = False
    self._Iter('DEAD run-isostream-server\n')
    isos.ServerTimeLimit = 1
    self.assertRaises(ValueError, lambda: setattr(isos, 'ServerTimeLimit', -1))
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    time.sleep(1)
    self._Iter('DEAD run-isostream-server\n')

  def testUnif(self):
    """Verify that our keyed uniform generator meets basic standards."""
    n = 0
    s_x = 0.0
    max_x = 0
    min_x = 1
    for vec in itertools.permutations('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 4):
      x = dm.isostream._Unif('1Catawampus4' + ''.join(vec))
      n += 1
      s_x += x
      min_x = min(min_x, x)
      max_x = max(max_x, x)

    self.assertAlmostEqual(0, min_x, places=3)
    self.assertAlmostEqual(0.5, s_x / n, places=3)
    self.assertAlmostEqual(1, max_x, places=3)

  def testClient(self):
    isos = dm.isostream.Isostream()
    self.assertEqual(isos.clientkey, '1CatawampusRocks')
    isos.ClientEnable = True
    self._Iter('run-isostream --use-storage-box -b 1\n')
    isos.ClientEnable = False
    self._Iter('DEAD run-isostream\n')

    # Test sufficient time.
    isos.ClientTimeSufficient = 10
    isos.ClientEnable = True
    self._Iter('run-isostream --use-storage-box -s 10 -b 1\n')
    isos.ClientEnable = False
    self._Iter('DEAD run-isostream\n')

    isos.ClientTimeSufficient = 0
    isos.ClientTimeLimit = 1
    self.assertRaises(ValueError, lambda: setattr(isos, 'ClientTimeLimit', 0))
    isos.ClientMbps = 99
    isos.ClientRemoteIP = '1.2.3.4'
    isos.ClientInterface = 'wcli0'
    isos.ClientEnable = True
    self._Iter('run-isostream 1.2.3.4 -I wcli0 -b 99\n')
    # Validate that we can run client and server at the same time
    isos.ServerEnable = True
    self._Iter('run-isostream-server\n')
    time.sleep(1)
    isos.ClientEnable = False
    self._Iter('DEAD run-isostream\n')
    isos.ServerEnable = False
    self._Iter('DEAD run-isostream-server\n')

  def testClientRekey(self):
    isos = dm.isostream.Isostream()
    tr.helpers.WriteFileAtomic(dm.isostream.CONSENSUS_KEY_FILE[0],
                               '1Catawampus4ever')
    self.loop.RunOnce()
    self.assertEqual(isos.clientkey, '1Catawampus4ever')

  def testClientScheduling(self):
    isos = dm.isostream.Isostream()
    clientWasRun = False
    isos.ClientRunOnSchedule = True
    isos.ClientTimeLimit = 1

    # Our scheduled interval can't overlap midnight. If we're close enough to
    # midnight that our interval would overlap, wait until midnight passes
    # to run the test.
    INTERVAL_LENGTH = 2
    lt = time.localtime()
    start, midnight = datetime.datetime(*lt[:6]), datetime.datetime(*lt[:3])
    offset = (start - midnight).seconds

    if offset <= (24*60*60 - (1 + INTERVAL_LENGTH)):
      isos.ClientStartAtOrAfter = offset + 1
    else:
      isos.ClientStartAtOrAfter = 1

    isos.ClientEndBefore = isos.ClientStartAtOrAfter + INTERVAL_LENGTH

    while (not clientWasRun and
           datetime.datetime.now() - start <=
           datetime.timedelta(seconds=2*INTERVAL_LENGTH+3)):
      self.loop.RunOnce()
      clientWasRun |= isos.ClientRunning
      time.sleep(0.1)

    self.assertTrue(clientWasRun)
    self.assertAlmostEqual(isos._GetNextDeadline() - datetime.timedelta(days=1),
                           datetime.timedelta(0),
                           delta=datetime.timedelta(1))
    self.assertTrue(isos.ClientDeadline)
    time.sleep(1)
    self._Iter('run-isostream --use-storage-box -b 1\nDEAD run-isostream\n')

  # pylint:disable=line-too-long
  def testParseLineToTuple(self):
    isos = dm.isostream.Isostream()
    isos.ParseLineToTuple('     29.428s 14Mbps offset=0.000s disconn=0/0.000s drops=9/0.047s/-0.098s')
    self.assertEqual(isos.last_log, dm.isostream.LogLine(29.428, 0.0, 0, 9))

    # the offset can become negative; this used to crash the parser.
    isos.ParseLineToTuple('     33.494s 14Mbps offset=-0.002s disconn=0/0.000s drops=10/0.068s/-0.098s')
    self.assertEqual(isos.last_log, dm.isostream.LogLine(33.494, -0.002, 0, 10))

  def testExperiments(self):
    # Test that isostream experiments don't raise exceptions when set;
    # this is a regression test for b/26829780.
    #
    # TODO(willangley): I see this as analogous to tr.handle.ValidateExports.
    # It's currently one-off for dm.isostream, but my hope is that we can
    # graduate this to something that lives in tr.experiment in a later CL, and
    # make this available to tests for all modules that declare experiments.

    root = dm_root.DeviceModelRoot(loop=None, platform=None, ext_dir='ext_test')
    mgmt = MockManagement()
    root.device = MockDevice()
    root.Device = MockTr181()
    root.InternetGatewayDevice = MockTr98()
    root.Export(objects=['Device', 'InternetGatewayDevice'])
    root.add_cwmp_extensions()
    root.add_management_server(mgmt)

    # Make sure we've only imported the isostream module once.
    self.assertEqual(type(root.Device.X_CATAWAMPUS_ORG.Isostream),
                     dm.isostream.Isostream)

    avail = root.X_CATAWAMPUS_ORG_CATAWAMPUS.Experiments.Available
    isostream_experiments = [ex for ex in avail.split(',') if 'Isostream' in ex]
    try:
      old_is_storage_box = dm.isostream.IS_STORAGE_BOX[0]
      for cmd in ['true', 'false']:
        dm.isostream.IS_STORAGE_BOX[0] = cmd
        for exp in isostream_experiments:
          root.X_CATAWAMPUS_ORG_CATAWAMPUS.Experiments.Requested = exp
    finally:
      dm.isostream.IS_STORAGE_BOX[0] = old_is_storage_box


if __name__ == '__main__':
  unittest.main()
