"""Tests for helpers."""

import os
import shutil
import tempfile
import unittest
import google3
import helpers


class HelpersTest(unittest.TestCase):
  """Unit tests for helpers.py."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

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


if __name__ == '__main__':
  unittest.main()
