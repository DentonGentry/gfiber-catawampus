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
#
# pylint:disable=invalid-name

"""Tests for helpers."""

import os
import shutil
import tempfile
from wvtest import unittest
import google3
import helpers


chowncalls = []


def FakeChown(filename, uid, gid):
  chown = (filename, uid, gid)
  chowncalls.append(chown)


class FakeDbThingy(object):

  def __init__(self):
    self.pw_uid = 1001
    self.gr_gid = 1002


def FakeGetUser(user):
  o = FakeDbThingy()
  if user == 'someuser':
    o.pw_uid = 10
  elif user == 'someotheruser':
    o.pw_uid = 20
  else:
    o.pw_uid = 1999
  return o


def FakeGetGroup(group):
  o = FakeDbThingy()
  if group == 'somegroup':
    o.gr_gid = 11
  elif group == 'someothergroup':
    o.gr_gid = 21
  else:
    o.gr_gid = 1888
  return o


class HelpersTest(unittest.TestCase):
  """Unit tests for helpers.py."""

  def setUp(self):
    self.CHOWN = helpers.CHOWN
    self.GETGID = helpers.GETGID
    self.GETUID = helpers.GETUID
    helpers.CHOWN = FakeChown
    helpers.GETGID = FakeGetGroup
    helpers.GETUID = FakeGetUser
    self.tmpdir = tempfile.mkdtemp()
    del chowncalls[:]

  def tearDown(self):
    shutil.rmtree(self.tmpdir)
    helpers.CHOWN = self.CHOWN
    helpers.GETGID = self.GETGID
    helpers.GETUID = self.GETUID

  def testUnlink(self):
    # should not raise an exception
    helpers.Unlink('./nonexistantfile')
    tmp = tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False)
    self.assertTrue(os.stat(tmp.name))
    helpers.Unlink(tmp.name)
    self.assertRaises(OSError, os.stat, tmp.name)

  def testWriteFileAtomic(self):
    content = 'Lorem ipsum, etcetera'
    filename = os.path.join(self.tmpdir, 'atomic.txt')
    helpers.WriteFileAtomic(filename, content)
    readback = open(filename).read()
    self.assertEqual(readback, content)

  def testAtomicFileWithOwner(self):
    content = 'Lorem ipsum, etcetera'
    filename = os.path.join(self.tmpdir, 'atomic.txt')
    tmpfilename = filename + '.tmp'
    helpers.WriteFileAtomic(filename, content, owner='someuser')
    helpers.WriteFileAtomic(filename, content,
                            owner='someotheruser',
                            group='somegroup')
    helpers.WriteFileAtomic(filename, content, group='someothergroup')
    self.assertEqual(len(chowncalls), 3)
    self.assertEqual(chowncalls[0], (tmpfilename, 10, -1))
    self.assertEqual(chowncalls[1], (tmpfilename, 20, 11))
    self.assertEqual(chowncalls[2], (tmpfilename, -1, 21))

  def testIsIPAddr(self):
    self.assertTrue(helpers.IsIP4Addr('1.2.3.4'))
    self.assertFalse(helpers.IsIP4Addr('1.2.3.1024'))
    self.assertFalse(helpers.IsIP4Addr('this is not an address'))
    self.assertTrue(helpers.IsIP6Addr('::1'))
    self.assertTrue(helpers.IsIP6Addr('100:1:a::1'))
    self.assertTrue(helpers.IsIP6Addr('100:1:a::'))
    self.assertFalse(helpers.IsIP6Addr('10000:1:a::'))
    self.assertFalse(helpers.IsIP6Addr('this is not an address'))

  def testNormalizeAddr(self):
    self.assertEqual('192.168.1.1', helpers.NormalizeIPAddr('192.168.1.1'))
    normal = helpers.NormalizeIPAddr('0000:0000:0000:0000:0000:0000:0000:0001')
    self.assertEqual('::1', normal)
    self.assertEqual(
        'fe80::21d:9ff:fe11:f55f',
        helpers.NormalizeIPAddr('fe80::21d:9ff:fe11:f55f'))
    self.assertEqual(
        'fe80::21d:9ff:fe11:f55f',
        helpers.NormalizeIPAddr('FE80::21D:9FF:FE11:F55F'))
    self.assertEqual('boo!', helpers.NormalizeIPAddr('boo!'))


if __name__ == '__main__':
  unittest.main()
