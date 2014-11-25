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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name
#
"""Tests for filenotifier.py."""

import os
import os.path
import shutil
import tempfile
import weakref
import google3
from wvtest import unittest
import tr.filenotifier
import tr.mainloop
import tr.pyinotify


class FileNotifierTest(unittest.TestCase):

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testFileNotifier(self):
    count = [0]
    def Incr1():
      count[0] += 1
    def Incr2():
      count[0] += 10
    def Incr3():
      count[0] += 100

    loop = tr.mainloop.MainLoop()
    n = tr.filenotifier.FileNotifier(loop)
    n_ref = weakref.ref(n)
    wm_ref = weakref.ref(n.wm)
    tornado_notifier_ref = weakref.ref(n.tornado_notifier)

    name1 = os.path.join(self.tmpdir, 'whatzit')
    name2 = os.path.join(self.tmpdir, 'whatzit2')
    name22 = os.path.join(self.tmpdir, 'sub/whatzit')
    n.Add(name1, Incr1)
    n.Add(name1, Incr1)  # should trigger twice
    n.Add(name2, Incr2)
    with self.assertRaises(tr.pyinotify.WatchManagerError):
      n.Add(name22, Incr3)

    os.makedirs(os.path.join(self.tmpdir, 'sub'))
    n.Add(name22, Incr3)

    print n.watches

    loop.RunOnce()
    self.assertEqual(count, [0])
    f = open(name1, 'w')
    loop.RunOnce()
    self.assertEqual(count, [0])
    f.close()
    loop.RunOnce()
    self.assertEqual(count, [2])
    loop.RunOnce()
    self.assertEqual(count, [2])
    os.rename(name1, name2)
    loop.RunOnce()
    self.assertEqual(count, [14])
    os.unlink(name2)
    loop.RunOnce()
    self.assertEqual(count, [24])
    open(name22, 'w').write('blah')
    loop.RunOnce()
    self.assertEqual(count, [124])

    self.assertEqual(len(n.watches), 2)
    n.Del(name1, Incr1)
    open(name1, 'w')
    loop.RunOnce()
    self.assertEqual(count, [125])
    os.rename(name1, name2)
    loop.RunOnce()
    self.assertEqual(count, [136])
    n.Del(name1, Incr1)
    os.rename(name2, name1)
    loop.RunOnce()
    self.assertEqual(count, [146])
    with self.assertRaises(KeyError):
      n.Del(name1, Incr1)
    n.Del(name2, Incr2)
    self.assertEqual(len(n.watches), 1)
    n.Del(name22, Incr3)
    self.assertEqual(len(n.watches), 0)

    # Check that deleting the notifier object actually frees it up, along
    # with its manager objects.  We check this by making sure that weakrefs
    # to the objects in question get invalidated when the original object
    # is deleted.
    try:
      # Generate a fake exception to clear out the saved exception stack,
      # and thus make sure all relevant refcounts are released.
      raise IOError()
    except IOError:
      pass
    self.assertTrue(n_ref())
    self.assertTrue(wm_ref())
    self.assertTrue(tornado_notifier_ref())
    del n
    print n_ref, wm_ref, tornado_notifier_ref
    print n_ref() and n_ref().watches
    self.assertFalse(n_ref())
    self.assertFalse(wm_ref())
    self.assertFalse(tornado_notifier_ref())

if __name__ == '__main__':
  unittest.main()
