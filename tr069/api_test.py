#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Test app for TR-069 CPE/ACS interface library."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import api
import objects
import unittest


class ApiTest(unittest.TestCase):
    def testApi(self):
        acs = api.ACS()
        cpe = api.CPE(acs)
        print acs.GetRPCMethods()
        print cpe.GetRPCMethods()
        (idx1, status) = cpe.AddObject('Test.', 0)
        (idx2, status) = cpe.AddObject('Test.Thingy.', 0)
        name1 = 'Test.%d' % idx1
        name2 = 'Test.Thingy.%d' % idx2
        print objects._objects[name1]
        print objects._objects[name2]
        cpe.SetParameterValues([('%s.word' % name1, 'word1')], 0)
        print objects._objects[name1]
        try:
            cpe.SetParameterValues([('%s.not_exist' % name1, 'word1')], 0)
        except KeyError:
            self.assertTrue('Got a KeyError - good.')
        else:
            self.assertTrue(0)
        result = cpe.GetParameterValues(['%s.word' % name1])
        print repr(result)
        self.assertEqual(result, [('%s.word' % name1, 'word1')])


if __name__ == '__main__':
  unittest.main()
