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
# pylint: disable-msg=C6409
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
    # pylint: disable-msg=W0612
    (idx, status) = cpe.AddObject('Test.Thingy.', 0)
    name = 'Test.Thingy.%d' % int(idx)
    # pylint: disable-msg=E1103
    cpe.SetParameterValues([('%s.word' % name, 'word1')], 0)
    self.assertEqual(root.GetExport(name).word, 'word1')
    self.assertRaises(KeyError, cpe._SetParameterValue,
                      '%s.not_exist' % name, 'word1')
    result = cpe.GetParameterValues(['%s.word' % name])
    self.assertEqual(result, [('%s.word' % name, 'word1')])

  def testGetParameterValuesEmpty(self):
    cpe = api.CPE(TestSimpleRoot())
    result = cpe.GetParameterValues([''])
    self.assertTrue(result)
    self.assertEqual(result[0], ('SomeParam', 'SomeParamValue'))


class ParameterAttrsTest(unittest.TestCase):
  def testSetAttr(self):
    class FakeAttrs(dict):
      def __getattr__(self, item):
        return self[item]

      def __setattr__(self, item, value):
        self[item] = value

    root = TestSimpleRoot()
    cpe = api.CPE(root)
    f = FakeAttrs()
    f.Name = 'SomeParam'
    f.Notification = 2
    cpe.SetParameterAttributes(f)
    self.assertEqual(len(cpe.parameter_attrs.params), 1)
    self.assertEqual(cpe.parameter_attrs.params['SomeParam'].notification, 0)

    f.Name = 'SomeParam'
    f.Notification = 2
    f.NotificationChange = 'true'
    cpe.SetParameterAttributes(f)
    self.assertEqual(len(cpe.parameter_attrs.params), 1)
    self.assertEqual(2, cpe.parameter_attrs.params['SomeParam'].notification)

    set_notification_arg = [[]]
    new_session_called = [0]

    def SetNotification(arg):
      set_notification_arg[0] += arg

    def NewSession():
      new_session_called[0] += 1

    cpe.parameter_attrs.set_notification_parameters_cb = SetNotification
    cpe.parameter_attrs.new_value_change_session_cb = NewSession

    # The value hasn't changed, so this shouldn't do anything.
    cpe.parameter_attrs.CheckForTriggers()
    self.assertEqual(0, len(set_notification_arg[0]))
    self.assertEqual(0, new_session_called[0])

    # Change the value and make sure a new session is triggered.
    root.SomeParam = 'NewValue'
    cpe.parameter_attrs.CheckForTriggers()
    self.assertEqual(1, len(set_notification_arg[0]))
    self.assertEqual('SomeParam', set_notification_arg[0][0][0])
    self.assertEqual('Trigger', set_notification_arg[0][0][1])
    self.assertEqual(1, new_session_called[0])


if __name__ == '__main__':
  unittest.main()
