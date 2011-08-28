#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Test app for TR-069 CPE/ACS interface library."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import api
import core
import unittest


class Word(core.Exporter):
    def __init__(self):
        core.Exporter.__init__(self)
        self.Export(params=['word'])
        self.word = None


class TestObject(core.Exporter):
    def __init__(self):
        core.Exporter.__init__(self)
        self.Export(lists=['Thingy'])
        self.ThingyList = {}
        self.Thingy = Word


class ApiTest(unittest.TestCase):
    def testApi(self):
        root = core.Exporter()
        root.Export(objects=['Test'])
        root.Test = TestObject()
        root.ValidateExports()
        acs = api.ACS()
        cpe = api.CPE(acs, root)
        print acs.GetRPCMethods()
        print cpe.GetRPCMethods()
        (idx, status) = cpe.AddObject('Test.Thingy.', 0)
        name = 'Test.Thingy.%d' % int(idx)
        print root.GetExport(name).word
        cpe.SetParameterValues([('%s.word' % name, 'word1')], 0)
        print root.GetExport(name).word
        try:
            cpe.SetParameterValues([('%s.not_exist' % name, 'word1')], 0)
        except KeyError:
            self.assertTrue('Got a KeyError - good.')
        else:
            self.assertTrue(0)
        result = cpe.GetParameterValues(['%s.word' % name])
        print repr(result)
        self.assertEqual(result, [('%s.word' % name, 'word1')])


if __name__ == '__main__':
  unittest.main()
