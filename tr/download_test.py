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
import time
import tornado.ioloop
import unittest

class PersistentObjectTest(unittest.TestCase):
  """Tests for download.py PersistentObject."""
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    download.statedir = self.tmpdir

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testPersistentObjectAttrs(self):
    kwargs = { "foo1" : "bar1", "foo2" : "bar2", "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    self.assertEqual(tobj.foo1, "bar1")
    self.assertEqual(tobj.foo2, "bar2")
    self.assertEqual(tobj.foo3, 3)

  def testStringifyXML(self):
    kwargs = { "foo1" : "bar1", "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    expected = """<TestObj><foo1 type="string">bar1</foo1><foo3 type="int">3</foo3></TestObj>"""
    self.assertEqual(str(tobj), expected)

  def testWriteToFile(self):
    kwargs = { "foo1" : "bar1", "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    expected = """<TestObj><foo1 type="string">bar1</foo1><foo3 type="int">3</foo3></TestObj>"""
    with open(tobj.filename) as f:
      actual = f.read()
    self.assertEqual(actual, expected)

  def testReadFromFile(self):
    contents = """<TestObj><foo type="string">bar</foo><baz type="int">4</baz></TestObj>"""
    with tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False) as f:
      f.write(contents)
      f.close()
      tobj = download.PersistentObject("TestObj", filename=f.name)
    self.assertEqual(tobj.foo, "bar")
    self.assertEqual(tobj.baz, 4)

  def testUpdate(self):
    kwargs = { "foo1" : "bar1", "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    expected = """<TestObj><foo1 type="string">bar1</foo1><foo3 type="int">3</foo3></TestObj>"""
    with open(tobj.filename) as f:
      actual = f.read()
    self.assertEqual(actual, expected)
    kwargs["foo1"] = "bar2"
    tobj.Update(**kwargs)
    expected = """<TestObj><foo1 type="string">bar2</foo1><foo3 type="int">3</foo3></TestObj>"""
    with open(tobj.filename) as f:
      actual = f.read()
    self.assertEqual(actual, expected)

  def testUpdateFails(self):
    kwargs = { "foo1" : "bar1",
               "foo3" : 3 }
    tobj = download.PersistentObject("TestObj", **kwargs)
    download.statedir = "/this_path_should_not_exist_hijhgvWRQ4MVVSDHuheifuh"
    kwargs["foo1"] = "bar2"
    self.assertRaises(OSError, tobj.Update, **kwargs)

  def testGetDownloadObjects(self):
    expected = ["""<tr69_dnld><foo type="string">bar1</foo><baz type="int">4</baz></tr69_dnld>""",
                """<tr69_dnld><foo type="string">bar2</foo><baz type="int">5</baz></tr69_dnld>""",
                """<tr69_dnld><foo type="string">bar3</foo><baz type="int">6</baz></tr69_dnld>"""]
    for obj in expected:
      with tempfile.NamedTemporaryFile(
          dir=self.tmpdir, prefix="tr69_dnld", delete=False) as f:
        f.write(obj)
        f.close()
    actual = download.GetDownloadObjects()
    self.assertEqual(len(actual), len(expected))
    found = [ False, False, False ]
    for entry in actual:
      if entry.foo == "bar1" and entry.baz == 4:
        found[0] = True
      if entry.foo == "bar2" and entry.baz == 5:
        found[1] = True
      if entry.foo == "bar3" and entry.baz == 6:
        found[2] = True
    self.assertTrue(found[0])
    self.assertTrue(found[1])
    self.assertTrue(found[2])


mock_http_clients = []
class MockHttpClient(object):
  def __init__(self):
    self.did_fetch = False
    self.request = None
    self.callback = None
    mock_http_clients.append(self)

  def fetch(self, request, callback):
    self.did_fetch = True
    self.request = request
    self.callback = callback


class MockIoloop(object):
  def __init__(self):
    self.time = None
    self.callback = None

  def add_timeout(self, time, callback):
    self.time = time
    self.callback = callback


class HttpDownloadTest(unittest.TestCase):
  """tests for download.py HttpDownload."""
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    download.statedir = self.tmpdir
    download.dnld_client = MockHttpClient

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testDelay(self):
    ioloop = MockIoloop()
    dl = download.HttpDownload(ioloop)
    delay = 100
    dl.download(delay_seconds=delay)
    self.assertTrue(ioloop.time is not None)
    delta = ioloop.time - time.time()
    # It is possible, though unlikely, that NTP adjusts our clock between
    # the call to dl.download and now. This test could then fail.
    self.assertTrue(delta <= delay)

  def testFetch(self):
    ioloop = MockIoloop()
    dl = download.HttpDownload(ioloop)
    username = "uname"
    password = "pword"
    url = "scheme://host:port/"
    dl.download(username=username, password=password, url=url)
    self.assertTrue(ioloop.time is not None)
    self.assertEqual(len(mock_http_clients), 0)

    # HttpDownload scheduled its callback, call it now.
    ioloop.callback()
    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.did_fetch)
    self.assertTrue(ht.request is not None)
    self.assertEqual(ht.request.auth_username, username)
    self.assertEqual(ht.request.auth_password, password)
    self.assertEqual(ht.request.url, url)


if __name__ == '__main__':
  unittest.main()
