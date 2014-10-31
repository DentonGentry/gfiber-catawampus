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
#pylint: disable-msg=C6409

"""Unit tests for gvsb.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import google3
import gvsb
from tr.wvtest import unittest
import tr.helpers
import tr.mainloop


def FakeChown(filename, uid, gid):
  return


class FakeDbThingy(object):
  def __init__(self):
    self.pw_uid = 0
    self.gr_gid = 0


def FakeGetUser(user):
  return FakeDbThingy()


def FakeGetGroup(group):
  return FakeDbThingy()


class GvsbTest(unittest.TestCase):
  """Tests for gvsb.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    tmpdir = tempfile.mkdtemp()
    self.EPGPRIMARYFILE = gvsb.EPGPRIMARYFILE
    self.EPGSECONDARYFILE = gvsb.EPGSECONDARYFILE
    self.EPGURLFILE = gvsb.EPGURLFILE
    self.GVSBSERVERFILE = gvsb.GVSBSERVERFILE
    self.GVSBCHANNELFILE = gvsb.GVSBCHANNELFILE
    self.GVSBKICKFILE = gvsb.GVSBKICKFILE
    self.CHOWN = tr.helpers.CHOWN
    self.GETGID = tr.helpers.GETGID
    self.GETUID = tr.helpers.GETUID
    gvsb.EPGPRIMARYFILE[0] = str(os.path.join(tmpdir, 'epgprimaryfile'))
    gvsb.EPGSECONDARYFILE[0] = str(os.path.join(tmpdir, 'epgsecondaryfile'))
    gvsb.EPGURLFILE[0] = str(os.path.join(tmpdir, 'epgurlfile'))
    gvsb.GVSBSERVERFILE[0] = str(os.path.join(tmpdir, 'gvsbserverfile'))
    gvsb.GVSBCHANNELFILE[0] = str(os.path.join(tmpdir, 'gvsbchannelfile'))
    gvsb.GVSBKICKFILE[0] = str(os.path.join(tmpdir, 'gvsbkickfile'))
    tr.helpers.CHOWN = FakeChown
    tr.helpers.GETGID = FakeGetGroup
    tr.helpers.GETUID = FakeGetUser
    self.tmpdir = tmpdir

  def tearDown(self):
    #shutil.rmtree(self.tmpdir)
    gvsb.EPGPRIMARYFILE = self.EPGPRIMARYFILE
    gvsb.EPGSECONDARYFILE = self.EPGSECONDARYFILE
    gvsb.EPGURLFILE = self.EPGURLFILE
    gvsb.GVSBSERVERFILE = self.GVSBSERVERFILE
    gvsb.GVSBCHANNELFILE = self.GVSBCHANNELFILE
    gvsb.GVSBKICKFILE = self.GVSBKICKFILE
    tr.helpers.CHOWN = tr.helpers.CHOWN
    tr.helpers.GETGID = tr.helpers.GETGID
    tr.helpers.GETUID = tr.helpers.GETUID

  def testValidateExports(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.ValidateExports()

  def _GetFileContent(self, filenamelist):
    filename = filenamelist[0]
    return open(filename).readline()

  def testEpgPrimary(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.EpgPrimary = 'EpgPrimaryFoo'
    self.loop.RunOnce()
    self.assertEqual(gv.EpgPrimary, 'EpgPrimaryFoo')
    self.assertEqual(self._GetFileContent(gvsb.EPGPRIMARYFILE), 'EpgPrimaryFoo\n')

  def testEpgSecondary(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.EpgSecondary = 'EpgSecondaryFoo'
    self.loop.RunOnce()
    self.assertEqual(gv.EpgSecondary, 'EpgSecondaryFoo')
    self.assertEqual(self._GetFileContent(gvsb.EPGSECONDARYFILE),
                     'EpgSecondaryFoo\n')

  def testEpgUrl(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.EpgUrl = 'EpgUrlFoo'
    self.loop.RunOnce()
    self.assertEqual(gv.EpgUrl, 'EpgUrlFoo')
    self.assertEqual(self._GetFileContent(gvsb.EPGURLFILE), 'EpgUrlFoo\n')

  def testGvsbServer(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.GvsbServer = 'GvsbServerFoo'
    self.loop.RunOnce()
    self.assertEqual(gv.GvsbServer, 'GvsbServerFoo')
    self.assertEqual(self._GetFileContent(gvsb.GVSBSERVERFILE),
                     'GvsbServerFoo\n')

  def testGvsbChannelLineup(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    self.assertEqual(gv.GvsbChannelLineup, '0')
    gv.GvsbChannelLineup = 1000
    self.loop.RunOnce()
    self.assertEqual(gv.GvsbChannelLineup, '1000')
    self.assertEqual(self._GetFileContent(gvsb.GVSBCHANNELFILE), '1000\n')

  def testGvsbKick(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    gv.GvsbKick = 'kickme'
    self.loop.RunOnce()
    self.assertEqual(gv.GvsbKick, 'kickme')
    self.assertEqual(self._GetFileContent(gvsb.GVSBKICKFILE), 'kickme\n')

  def _FileIsEmpty(self, filenamelist):
    """Check that file exists but is zero bytes in size."""
    filename = filenamelist[0]
    st = os.stat(filename)
    return True if st and st.st_size == 0 else False

  def testInitEmptyFiles(self):
    gv = gvsb.Gvsb()
    self.loop.RunOnce()
    self.assertTrue(self._FileIsEmpty(gvsb.EPGPRIMARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.EPGSECONDARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.EPGURLFILE))
    self.assertFalse(self._FileIsEmpty(gvsb.GVSBCHANNELFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBSERVERFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBKICKFILE))


if __name__ == '__main__':
  unittest.main()
