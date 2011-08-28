#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Tests for objects.py.."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import objects
import unittest

gcount = 0

class SubObj(objects.ParameterizedObject):
    def __init__(self):
        objects.ParameterizedObject.__init__(self)
        self.Export(params=['Count'])
        
        global gcount
        gcount += 1
        self.Count = gcount


class TestObject(objects.ParameterizedObject):
    def __init__(self):
        objects.ParameterizedObject.__init__(self)
        self.Export(params=['TestParam'],
                    objects=['TestObj'],
                    lists=['Counter'])
        self.TestParam = 5
        self.TestObj = SubObj()
        self.CounterList = {}
        self.Counter = SubObj


class ObjectsTest(unittest.TestCase):
    def testObjects(self):
        o = TestObject()
        self.assertTrue(o)
        o.ValidateExports()
        o.AddExportObject('Counter')
        o.AddExportObject('Counter')
        o.AddExportObject('Counter')
        print o.ListExports(recursive=False)
        print o.ListExports(recursive=True)
        self.assertEqual(o.ListExports(),
                         ['Counter.', 'TestObj.', 'TestParam'])
        self.assertEqual(o.ListExports(recursive=True),
                         ['Counter.', 'Counter.0.Count',
                          'Counter.1.Count', 'Counter.2.Count',
                          'TestObj.', 'TestObj.Count', 'TestParam'])
        o.DeleteExportObject('Counter', 1)
        self.assertEqual(o.ListExports(recursive=True),
                         ['Counter.', 'Counter.0.Count',
                          'Counter.2.Count',
                          'TestObj.', 'TestObj.Count', 'TestParam'])
        self.assertEqual([(idx,i.Count) for idx,i in o.CounterList.items()],
                         [('0',2),('2',4)])
        eo = o.AddExportObject('Counter', 'fred')
        eo.Count = 99
        print o.ListExports(recursive=True)
        self.assertEqual([(idx,i.Count) for idx,i in o.CounterList.items()],
                         [('0',2),('2',4),('fred',99)])
        print objects.Dump(o)


if __name__ == '__main__':
  unittest.main()
