#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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
# pylint:disable=unused-argument
#
"""Tests for core.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import weakref
import core
import handle
from wvtest import unittest


class TestObject(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['TestParam'],
                objects=['SubObj'],
                lists=['Counter'])
    self.TestParam = 5
    self.SubObj = TestObject.SubObj()
    self.CounterList = {}
    self.Counter = TestObject.SubObj

  class SubObj(core.Exporter):
    gcount = [0]

    def __init__(self):
      core.Exporter.__init__(self)
      self.Export(params=['Count'])

      self.gcount[0] += 1
      self.Count = self.gcount[0]


class AutoObject(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.SubList = core.AutoDict('SubList',
                                 iteritems=self._itersubs,
                                 getitem=self._getsub)
    self.Export(lists=['Sub'])

  def _itersubs(self):
    for i in range(3):
      yield i, self.Sub(i)

  def _getsub(self, key):
    return self.Sub(int(key))

  class Sub(core.Exporter):
    gcount = [0]

    def __init__(self, i):
      core.Exporter.__init__(self)
      self.Export(params=['Count'])
      self.gcount[0] += 1
      self.Count = self.gcount[0]


class CoreTest(unittest.TestCase):

  def setUp(self):
    # Reset the global gcount
    TestObject.SubObj.gcount = [0]

  def testCore(self):
    o = TestObject()
    h = handle.Handle(o)
    self.assertTrue(o)
    h.ValidateExports()
    h.AddExportObject('Counter')
    h.AddExportObject('Counter')
    h.AddExportObject('Counter')
    print h.ListExports(recursive=False)
    print h.ListExports(recursive=True)
    self.assertEqual(list(h.ListExports()),
                     ['Counter.', 'SubObj.', 'TestParam'])
    self.assertEqual(list(h.ListExports(recursive=True)),
                     ['Counter.',
                      'Counter.1.', 'Counter.1.Count',
                      'Counter.2.', 'Counter.2.Count',
                      'Counter.3.', 'Counter.3.Count',
                      'SubObj.', 'SubObj.Count', 'TestParam'])

    ds1 = handle.DumpSchema(TestObject)
    ds2 = handle.DumpSchema(o)
    self.assertEqual(ds1, ds2)

    h.DeleteExportObject('Counter', 2)
    self.assertEqual(list(h.ListExports(recursive=True)),
                     ['Counter.',
                      'Counter.1.', 'Counter.1.Count',
                      'Counter.3.', 'Counter.3.Count',
                      'SubObj.', 'SubObj.Count', 'TestParam'])
    self.assertEqual([(idx, i.Count) for idx, i in o.CounterList.items()],
                     [(1, 2), (3, 4)])
    # NOTE(jnewlin): Note that is actually outside the spec, the spec says that
    # the index is an integer, but I guess it's neat that we can do this.
    idx, eo = h.AddExportObject('Counter', 'fred')
    eo.Count = 99
    print h.ListExports(recursive=True)
    self.assertEqual([(idx, i.Count) for idx, i in o.CounterList.items()],
                     [(1, 2), (3, 4), ('fred', 99)])
    print handle.Dump(o)
    h.ValidateExports()

  def testCanonicalName(self):
    o = TestObject()
    h = handle.Handle(o)
    self.assertTrue(o)
    h.ValidateExports()
    name = handle.Handle.GetCanonicalName(o, o.SubObj)
    self.assertEqual('SubObj', name)

    (unused_idx1, unused_obj1) = h.AddExportObject('Counter')
    (unused_idx2, unused_obj2) = h.AddExportObject('Counter')
    (unused_idx3, obj3) = h.AddExportObject('Counter')
    name = handle.Handle.GetCanonicalName(o, obj3)
    self.assertEqual('Counter.3', name)

  def testLifecycle(self):
    # AutoObject() regenerates its children, with a new count, every time
    # you look for them.  (This simulates a "virtual" hierarchy, such as
    # a Unix process list, that is different every time you look at it.)
    # However, we should expect that if we retrieve multiple values at once,
    # they all refer to the same instance of an object.
    #
    # The Count parameter is generated sequentially each time AutoObject
    # creates a child, and we can use that to confirm that the code doesn't
    # do unnecessary tree traversals without caching intermediate objects.
    root = AutoObject()
    h = handle.Handle(root)
    s0 = root.SubList[0]
    self.assertEqual(s0.Count, 1)
    self.assertEqual(s0.Count, 1)
    self.assertEqual(root.SubList[0].Count, 2)
    self.assertEqual(s0.Count, 1)  # old object still exists
    w = weakref.ref(s0)
    self.assertEqual(s0, w())
    del s0
    self.assertEqual(w(), None)  # all remaining refs are definitely gone
    self.assertEqual(handle.Handle(root.SubList[0]).GetExport('Count'), 3)

    # FindExport of Sub.0 shouldn't actually instantiate the .0
    hp = h.FindExport('Sub.0')
    self.assertEqual((hp[0].obj, hp[1]), (root.SubList, '0'))
    self.assertEqual(root.SubList[0].Count, 4)

    # FindExport of Sub.0.Count should instantiate Sub.0 exactly once
    s0, name = h.FindExport('Sub.0.Count')
    self.assertEqual(name, 'Count')
    self.assertEqual(s0.obj.Count, 5)
    self.assertEqual(s0.obj.Count, 5)

    self.assertEqual(handle.Handle(root.SubList[0]).GetExport('Count'), 6)
    self.assertEqual(h.GetExport('Sub.0.Count'), 7)
    self.assertEqual(h.GetExport('Sub.576.Count'), 8)

    self.assertEqual(list(h.ListExports(recursive=False)),
                     ['Sub.'])
    self.assertEqual(root.SubList[0].Count, 9)

    self.assertEqual(list(h.ListExports(recursive=True)),
                     ['Sub.',
                      'Sub.0.',
                      'Sub.0.Count',
                      'Sub.1.',
                      'Sub.1.Count',
                      'Sub.2.',
                      'Sub.2.Count'])
    self.assertEqual(root.SubList[0].Count, 13)

    # LookupExports gives us a list of useful object pointers that
    # should only generate each requested object once.
    print 'lookup test'
    out = list(h.LookupExports(['Sub.0.Count',
                                'Sub.1.Count',
                                'Sub.0.Count',
                                'Sub.1.',
                                'Sub.',
                                '.']))
    s0 = out[0][0].obj
    s1 = out[1][0].obj
    self.assertEqual([(io.obj, iname) for (io, iname) in out],
                     [(s0, 'Count'),
                      (s1, 'Count'),
                      (s0, 'Count'),
                      (s1, ''),
                      (root.SubList, ''),
                      (root, '')])
    vals = [getattr(o.obj, param) for o, param in out[0:3]]
    self.assertEqual(vals, [14, 15, 14])
    vals = [getattr(o.obj, param) for o, param in out[0:3]]
    self.assertEqual(vals, [14, 15, 14])

    out = list(h.LookupExports(['Sub.1.Count',
                                'Sub.0.Count',
                                'Sub.1.Count']))
    self.assertNotEqual(out[1][0], s0)
    self.assertNotEqual(out[0][0], s1)
    s0 = out[1][0].obj
    s1 = out[0][0].obj
    self.assertEqual([s0.Count, s1.Count], [17, 16])
    for i, (o, param) in enumerate(out):
      setattr(o, param, i * 1000)
    vals = [getattr(o, param) for o, param in out]
    self.assertEqual(vals, [2000, 1000, 2000])


if __name__ == '__main__':
  unittest.main()
