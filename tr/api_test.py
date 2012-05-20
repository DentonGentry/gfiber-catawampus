#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""Test app for TR-069 CPE/ACS interface library."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest

import google3
import api
import core


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


class TestSimpleRoot(core.Exporter):
  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['SomeParam'])
    self.SomeParam = 'SomeParamValue'


class ApiTest(unittest.TestCase):
  def testObject(self):
    root = core.Exporter()
    root.Export(objects=['Test'])
    root.Test = TestObject()
    root.ValidateExports()
    cpe = api.CPE(root)
    #pylint: disable-msg=W0612
    (idx, status) = cpe.AddObject('Test.Thingy.', 0)
    name = 'Test.Thingy.%d' % int(idx)
    #pylint: disable-msg=E1103
    cpe.SetParameterValues([('%s.word' % name, 'word1')], 0)
    self.assertEqual(root.GetExport(name).word, 'word1')
    self.assertRaises(KeyError, cpe.SetParameterValues,
                      [('%s.not_exist' % name, 'word1')], 0)
    result = cpe.GetParameterValues(['%s.word' % name])
    self.assertEqual(result, [('%s.word' % name, 'word1')])

  def testGetParameterValuesEmpty(self):
    cpe = api.CPE(TestSimpleRoot())
    result = cpe.GetParameterValues([''])
    self.assertTrue(result)
    self.assertEqual(result[0], ('SomeParam', 'SomeParamValue'))


if __name__ == '__main__':
  unittest.main()
