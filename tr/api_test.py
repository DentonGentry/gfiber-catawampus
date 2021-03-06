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
#
"""Test app for TR-069 CPE/ACS interface library."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import google3
import tr.cwmptypes
import api
import core
import handle
from wvtest import unittest


changes = 0


class Word(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['word', 'readonlyword'])
    self._word = None

  @property
  def word(self):
    return self._word

  @word.setter
  def word(self, value):
    global changes
    changes += 1
    self._word = value

  @property
  def readonlyword(self):
    return 'cant-write-me!'

  validatedword = tr.cwmptypes.String()

  @validatedword.validator
  def validatedword(self, value):
    if value not in ['yes', 'no']:
      raise ValueError('must be yes or no')
    return value


class IndexErrorDict(object):

  def __init__(self):
    self.fault = False
    self.item = Word()

  def iteritems(self):
    return [(1, self.item), (2, self.item)]

  def __getitem__(self, _):
    if self.fault:
      raise IndexError('unit test')
    return self.item


class TestObject(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(lists=['Thingy', 'AutoThingy', 'IndexErrorThingy'])
    self.ThingyList = {}
    self.Thingy = Word
    self.IndexErrorThingyList = IndexErrorDict()
    self.NumAutoThingies = 5

  @property
  def AutoThingyList(self):
    rc = {}
    for i in range(self.NumAutoThingies):
      rc[str(i + 1)] = Word()
    return rc


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
    h = handle.Handle(root)
    h.ValidateExports()
    cpe = api.CPE(h)
    (idx, unused_status) = cpe.AddObject('Test.Thingy.', 0)
    name = 'Test.Thingy.%d' % int(idx)
    cpe.SetParameterValues([('%s.word' % name, 'word1')], 0)
    self.assertEqual(h.GetExport(name).word, 'word1')
    self.assertRaises(KeyError, cpe._SetParameterValue,
                      '%s.not_exist' % name, 'word1')
    result = cpe.GetParameterValues(['%s.word' % name])
    self.assertEqual(result, [('%s.word' % name, 'word1')])
    self.assertEqual(changes, 1)
    self.assertRaises(api.SetParameterErrors,
                      cpe.SetParameterValues,
                      [('%s.word' % name, 'snorkleberry'),
                       ('nonexist', 'broken')], 0)
    # word was not changed because nonexist didn't exist and we check for
    # existence first.
    self.assertEqual(result, [('%s.word' % name, 'word1')])
    self.assertEqual(changes, 1)

    # word changed, but then changed back, because readonlyword has no
    # validator and it failed in the set phase.
    self.assertRaises(api.SetParameterErrors,
                      cpe.SetParameterValues,
                      [('%s.word' % name, 'snorkleberry'),
                       ('%s.readonlyword' % name, 'broken')], 0)
    self.assertEqual(result, [('%s.word' % name, 'word1')])
    self.assertEqual(changes, 3)

    # word changed, but then changed back.  Strictly speaking we could have
    # aborted the set as soon as reasonlyword failed, but then the set of
    # error messages wouldn't be as thorough as possible, so we deliberately
    # choose to try all the sets if we get to the setting phase.
    self.assertRaises(api.SetParameterErrors,
                      cpe.SetParameterValues,
                      [('%s.readonlyword' % name, 'broken'),
                       ('%s.word' % name, 'snorkleberry')], 0)
    self.assertEqual(result, [('%s.word' % name, 'word1')])
    self.assertEqual(changes, 5)

    self.assertRaises(api.SetParameterErrors,
                      cpe.SetParameterValues,
                      [('%s.word' % name, 'snorkleberry'),
                       ('%s.validatedword' % name, 'broken')], 0)
    self.assertEqual(result, [('%s.word' % name, 'word1')])
    self.assertEqual(changes, 5)

    (objidx_list, status) = cpe.X_CATAWAMPUS_ORG_AddObjects(
        [('Test.Thingy.', 5), ('Test.Thingy.', 2)], 0)
    self.assertEqual(status, 0)
    self.assertEqual(len(objidx_list), 2)
    idxlist = objidx_list[0][1] + objidx_list[1][1]
    self.assertEqual(len(set(idxlist)), 7)
    result = cpe.GetParameterValues([('Test.Thingy.%d' % int(idx))
                                     for idx in idxlist])
    self.assertEqual([i.word for idx, i in result],
                     [None] * 7)

  def testGetParameterValuesEmpty(self):
    cpe = api.CPE(handle.Handle(TestSimpleRoot()))
    result = cpe.GetParameterValues([''])
    self.assertTrue(result)
    self.assertEqual(result[0], ('SomeParam', 'SomeParamValue'))


class FakeAttrs(dict):
  """Helper class used for testing Attributes."""

  def __getattr__(self, item):
    return self[item]

  def __setattr__(self, item, value):
    self[item] = value


def RaiseAttributeError(*unused_args):
  raise AttributeError('foo!')


def RaiseTypeError(*unused_args):
  raise TypeError('bar!')


def RaiseValueError(*unused_args):
  raise ValueError('baz!')


def RaiseKeyError(*unused_args):
  raise KeyError('boo!')


def RaiseIOError(*unused_args):
  raise IOError('far!')


set_notification_arg = [[]]
new_session_called = [0]


def SetNotification(arg):
  set_notification_arg[0] += arg


def NewSession():
  new_session_called[0] += 1


class ParameterAttrsTest(unittest.TestCase):

  def setUp(self):
    set_notification_arg[0] = []
    new_session_called[0] = 0

  def testSetAttr(self):
    root = TestSimpleRoot()
    cpe = api.CPE(handle.Handle(root))
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
    self.assertEqual(root.SomeParam, set_notification_arg[0][0][1])
    self.assertEqual(1, new_session_called[0])

  def testDeleteParam(self):
    root = TestObject()
    cpe = api.CPE(handle.Handle(root))
    (unused_idx, unused_obj) = cpe.AddObject('Thingy.', '1')
    f = FakeAttrs()
    f.Name = 'Thingy.1'
    f.Notification = 2
    cpe.SetParameterAttributes(f)
    self.assertEqual(len(cpe.parameter_attrs.params), 1)
    cpe.DeleteObject('Thingy.1.', 'fake-key')
    self.assertEqual(len(cpe.parameter_attrs.params), 0)

  def testNonexistent(self):
    root = TestObject()
    cpe = api.CPE(handle.Handle(root))

    cpe.parameter_attrs.set_notification_parameters_cb = SetNotification
    cpe.parameter_attrs.new_value_change_session_cb = NewSession

    f = FakeAttrs()
    f.Name = 'AutoThingy.3'
    f.Notification = 2
    f.NotificationChange = 'true'
    cpe.SetParameterAttributes(f)
    self.assertEqual(len(cpe.parameter_attrs.params), 1)
    root.NumAutoThingies = 1

    # Check that this doesn't raise an exception
    cpe.parameter_attrs.CheckForTriggers()
    self.assertEqual(0, len(set_notification_arg[0]))

    root.NumAutoThingies = 5
    self.assertEqual(0, len(set_notification_arg[0]))

    root.AutoThingyList['3'].word = 'word1'
    cpe.parameter_attrs.CheckForTriggers()
    self.assertEqual(1, len(set_notification_arg[0]))

  def testIndexError(self):
    root = TestObject()
    cpe = api.CPE(handle.Handle(root))

    cpe.parameter_attrs.set_notification_parameters_cb = SetNotification
    cpe.parameter_attrs.new_value_change_session_cb = NewSession

    f = FakeAttrs()
    f.Name = 'IndexErrorThingy.3'
    f.Notification = 2
    f.NotificationChange = 'true'
    cpe.SetParameterAttributes(f)
    self.assertEqual(len(cpe.parameter_attrs.params), 1)
    root.NumAutoThingies = 1

    # Check that this doesn't raise an exception
    root.IndexErrorThingyList.fault = True
    cpe.parameter_attrs.CheckForTriggers()
    self.assertEqual(0, len(set_notification_arg[0]))

  def testSetAttrErrors(self):
    root = TestSimpleRoot()
    cpe = api.CPE(handle.Handle(root))
    error_list = []
    cpe._Apply(error_list, 'fullname', api.ParameterNotWritableError,
               RaiseAttributeError, [])
    cpe._Apply(error_list, 'fullname', None, RaiseTypeError, [])
    cpe._Apply(error_list, 'fullname', None, RaiseValueError, [])
    cpe._Apply(error_list, 'fullname', None, RaiseKeyError, [])
    cpe._Apply(error_list, 'fullname', None, RaiseIOError, [])
    self.assertEqual(5, len(error_list))
    self.assertEqual(api.ParameterNotWritableError, type(error_list[0]))
    self.assertEqual(api.ParameterTypeError, type(error_list[1]))
    self.assertEqual(api.ParameterValueError, type(error_list[2]))
    self.assertEqual(api.ParameterNameError, type(error_list[3]))
    self.assertEqual(api.ParameterInternalError, type(error_list[4]))


if __name__ == '__main__':
  unittest.main()
