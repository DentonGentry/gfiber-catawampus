"""Tests for helpers."""

import os
import shutil
import tempfile
import unittest
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


if __name__ == '__main__':
  unittest.main()
