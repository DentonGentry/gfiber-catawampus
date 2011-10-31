#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for download.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import download
import os
import shutil
import tempfile
import unittest

class PersistentObjectTest(unittest.TestCase):
  """Tests for download.py."""
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    download.statedir = self.tmpdir

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testPersistentObjectAttrs(self):
    kwargs = { "foo1" : "bar1",
               "foo2" : "bar2",
               "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    self.assertEqual(tobj.foo1, "bar1")
    self.assertEqual(tobj.foo2, "bar2")
    # PersistentObject makes everything a string
    self.assertEqual(tobj.foo3, "3")

  def testStringifyXML(self):
    kwargs = { "foo1" : "bar1",
               "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    expected = "<TestObj><foo1>bar1</foo1><foo3>3</foo3></TestObj>"
    self.assertEqual(str(tobj), expected)

  def testWriteToFile(self):
    kwargs = { "foo1" : "bar1",
               "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    expected = "<TestObj><foo1>bar1</foo1><foo3>3</foo3></TestObj>"
    with open(tobj.filename) as f:
      actual = f.read()
    self.assertEqual(actual, expected)

  def testReadFromFile(self):
    contents = "<TestObj><foo>bar</foo><baz>4</baz></TestObj>"
    with tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False) as f:
      f.write(contents)
      f.close()
      tobj = download.PersistentObject("TestObj", filename=f.name)
    self.assertEqual(tobj.foo, "bar")
    self.assertEqual(tobj.baz, "4")


if __name__ == '__main__':
  unittest.main()
