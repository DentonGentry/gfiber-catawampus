#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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
"""Tests for types.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import datetime
import os.path
import time
from wvtest import unittest
import google3
import mainloop
import tr.cwmptypes


TEST_FILE = 'testobject.tmp'
TEST2_FILE = 'testobject2.tmp'
TEST3_FILE = '/this/file/does/not/exist/i/hope'


class TestObject(object):
  a = tr.cwmptypes.Attr()
  b = tr.cwmptypes.Bool()
  s = tr.cwmptypes.String('defaultstring')
  i = tr.cwmptypes.Int()
  u = tr.cwmptypes.Unsigned()
  f = tr.cwmptypes.Float(4)
  e = tr.cwmptypes.Enum(['one', 'two', 'three', 7, None])
  e2 = tr.cwmptypes.Enum(['thing'])
  d = tr.cwmptypes.Date()
  m = tr.cwmptypes.MacAddr(init='')
  ip4 = tr.cwmptypes.IP4Addr()
  ip6 = tr.cwmptypes.IP6Addr()
  file = tr.cwmptypes.FileBacked([TEST_FILE], tr.cwmptypes.Bool())
  file2 = tr.cwmptypes.FileBacked([TEST_FILE], tr.cwmptypes.Bool(),
                                  delete_if_empty=False)
  file3 = tr.cwmptypes.FileBacked([TEST3_FILE], tr.cwmptypes.String())

  v = tr.cwmptypes.Unsigned()

  @v.validator
  def v(self, value):
    return value * self.f

  vv = tr.cwmptypes.Int()

  @vv.validator
  def vv(self, value):
    return -value

  @vv.validator
  def vv(self, value):
    return value + 1


class NotifierTestObject(object):
  a = tr.cwmptypes.Int(0)
  b = tr.cwmptypes.Int(5)


def ChangeValues(obj):
  obj.b = obj.a


class TriggerObject(object):

  def __init__(self):
    self.xval = 7
    self.triggers = 0

  def Triggered(self):
    self.triggers += 1

  @property
  def val(self):
    return self.xval

  @tr.cwmptypes.Trigger
  @val.setter
  def val(self, value):
    self.xval = value

  a = tr.cwmptypes.Trigger(tr.cwmptypes.Attr())
  b = tr.cwmptypes.TriggerBool()
  i = tr.cwmptypes.TriggerInt()
  m = tr.cwmptypes.TriggerMacAddr(init='')
  ip4 = tr.cwmptypes.TriggerIP4Addr('1.2.3.4')
  ip6 = tr.cwmptypes.TriggerIP6Addr('1111:2222::3333:4444')

  v = tr.cwmptypes.TriggerFloat()

  @v.validator
  def v(self, value):
    return value + 1

  vv = tr.cwmptypes.Float()

  @vv.validator
  def vv(self, value):
    return 2 * value
  vv = tr.cwmptypes.Trigger(vv)


class ReadOnlyObject(object):
  b = tr.cwmptypes.ReadOnlyBool(True)
  d = tr.cwmptypes.ReadOnlyDate(0.0)
  i = tr.cwmptypes.ReadOnlyInt('5')
  s = tr.cwmptypes.ReadOnlyString('foo')
  e = tr.cwmptypes.ReadOnlyEnum(['x', 'y', 'z'])
  u = tr.cwmptypes.ReadOnlyUnsigned(6)
  m = tr.cwmptypes.ReadOnlyMacAddr('00:11:22:33:44:55')
  ip4 = tr.cwmptypes.ReadOnlyIP4Addr('1.2.3.4')
  ip6 = tr.cwmptypes.ReadOnlyIP6Addr('1111:2222::3333:4444')


class NumberOfObject(object):
  TestDictNumberOfEntries = tr.cwmptypes.NumberOf('TestDict')
  TestListNumberOfEntries = tr.cwmptypes.NumberOf('TestList')

  def __init__(self):
    self.TestDict = {}
    self.TestList = []


class TypesTest(unittest.TestCase):

  def testTypes(self):
    obj = TestObject()
    self.assertEquals(obj.a, None)
    self.assertEquals(obj.b, None)
    self.assertEquals(obj.s, 'defaultstring')
    self.assertEquals(obj.i, None)
    self.assertEquals(obj.e, None)
    self.assertEquals(obj.e2, None)
    self.assertEquals(obj.d, None)
    self.assertEquals(obj.m, None)
    self.assertEquals(obj.ip4, None)
    self.assertEquals(obj.ip6, None)
    o1 = object()

    obj.a = o1
    self.assertEquals(obj.a, o1)
    obj.a = None
    self.assertEquals(obj.a, None)

    obj.b = 0
    self.assertEquals(obj.b, 0)
    self.assertNotEqual(obj.b, None)
    obj.b = False
    self.assertEquals(obj.b, 0)
    obj.b = 'FaLSe'
    self.assertEquals(obj.b, 0)
    self.assertTrue(obj.b is False)
    self.assertTrue(obj.b is not 0)
    obj.b = ''
    self.assertEquals(obj.b, 0)
    obj.b = 'tRuE'
    self.assertEquals(obj.b, 1)
    self.assertTrue(obj.b is True)
    self.assertTrue(obj.b is not 1)
    obj.b = '5'
    self.assertTrue(obj.b is True)
    self.assertRaises(ValueError, setattr, obj, 'b', object())
    self.assertRaises(ValueError, setattr, obj, 'b', [])
    self.assertFalse(hasattr(obj.b, 'xsitype'))

    self.assertEquals(obj.s, 'defaultstring')
    obj.s = 1
    self.assertEquals(obj.s, '1')
    obj.s = o1
    self.assertEquals(obj.s, str(o1))
    obj.s = None
    self.assertEquals(obj.s, None)
    self.assertNotEqual(obj.s, str(None))
    obj.s = ''
    self.assertEquals(obj.s, '')
    self.assertNotEqual(obj.s, None)

    obj.i = 7
    self.assertEquals(obj.i, 7)
    obj.i = '8'
    self.assertEquals(obj.i, 8)
    self.assertEquals(obj.i.xsitype, 'xsd:int')
    self.assertRaises(ValueError, setattr, obj, 'i', '')

    obj.u = '5'
    self.assertEquals(obj.u, 5)
    self.assertEquals(obj.u.xsitype, 'xsd:unsignedInt')
    obj.u = 0
    self.assertEquals(obj.u, 0)
    self.assertRaises(ValueError, setattr, obj, 'u', '-5')
    self.assertRaises(ValueError, setattr, obj, 'u', -5)

    obj.f = '5'
    self.assertEquals(obj.f, 5.0)
    obj.f = 0
    self.assertEquals(obj.f, 0)
    obj.f = 5e60
    self.assertEquals(obj.f, 5e60)

    obj.e = 'one'
    self.assertEquals(obj.e, 'one')
    obj.e = 7
    self.assertEquals(obj.e, 7)
    self.assertRaises(ValueError, setattr, obj, 'e', '7')
    obj.e = None

    obj.e2 = 'thing'
    self.assertRaises(ValueError, setattr, obj, 'e2', None)

    obj.f = 11.5
    self.assertEquals(tr.cwmptypes.tryattr(obj, 'v', 3.4), int(int(3.4) * 11.5))
    self.assertRaises(ValueError, setattr, obj, 'v', -1)
    obj.v = 7.3
    self.assertEquals(obj.v, int(int(7.3) * 11.5))

    obj.vv = 5  # validator chain is: -((-5) + 1)
    self.assertEquals(obj.vv, 4)

    obj.d = 0
    self.assertEquals(obj.d, datetime.datetime.utcfromtimestamp(0))
    now = time.time()
    obj.d = now
    self.assertEquals(obj.d, datetime.datetime.utcfromtimestamp(now))
    obj.d = ''
    self.assertEquals(obj.d, None)
    obj.d = '2013-02-27T12:17:37Z'
    self.assertEquals(obj.d, datetime.datetime.utcfromtimestamp(1361967457))

    obj.m = '00:11:22:33:44:55'
    self.assertEquals(obj.m, '00:11:22:33:44:55')
    obj.m = '00-11-22-33-44-55'
    self.assertEquals(obj.m, '00-11-22-33-44-55')
    self.assertRaises(ValueError, setattr, obj, 'm', 1)

    obj.ip4 = '2.3.4.5'
    self.assertEquals(obj.ip4, '2.3.4.5')
    self.assertRaises(ValueError, setattr, obj, 'ip4', 1)

    obj.ip6 = '2222::'
    self.assertEquals(obj.ip6, '2222::')
    self.assertRaises(ValueError, setattr, obj, 'ip6', 1)

    open(TEST_FILE, 'w').write('5')
    self.assertEquals(obj.file, 1)
    open(TEST_FILE, 'w').write('0')
    self.assertEquals(obj.file, 0)
    obj.file = ''
    loop = mainloop.MainLoop()
    loop.RunOnce()
    self.assertTrue(os.path.exists(TEST_FILE))
    self.assertEquals(open(TEST_FILE).read(), 'False\n')
    obj.file = None
    loop.RunOnce()
    self.assertFalse(os.path.exists(TEST_FILE))
    obj.file = -900
    loop.RunOnce()
    self.assertEquals(open(TEST_FILE).read(), 'True\n')
    os.unlink(TEST_FILE)

  def testFileBackedTransactions(self):
    loop = mainloop.MainLoop()
    obj = TestObject()
    saved = obj.file
    obj.file = '1'
    self.assertEqual(obj.file, saved)
    obj.file = saved
    self.assertEqual(obj.file, saved)
    # Simulates an abandoned transaction
    loop.RunOnce()
    self.assertEqual(obj.file, saved)
    saved = obj.file
    obj.file = '1'
    self.assertEqual(obj.file, saved)
    # Simulates a successful transaction
    loop.RunOnce()
    self.assertTrue(obj.file)

  def testFileBackedNotDeleted(self):
    obj = TestObject()
    open(TEST2_FILE, 'w').write('0')
    self.assertEquals(obj.file2, False)
    obj.file2 = ''
    loop = mainloop.MainLoop()
    loop.RunOnce()
    self.assertTrue(os.path.exists(TEST2_FILE))
    obj.file2 = None
    loop.RunOnce()
    self.assertTrue(os.path.exists(TEST2_FILE))
    os.unlink(TEST2_FILE)

  def testFileBackedNotExist(self):
    obj = TestObject()
    with self.assertRaises(IOError):
      obj.file3 = 'this should assert!'
    loop = mainloop.MainLoop()
    loop.RunOnce()

  def testTypeCoercion(self):
    obj = TestObject()
    obj.b = True
    obj.i = 7
    obj.f = 3.14
    obj.s = '5'
    obj.u = 2
    # Mostly we're checking that no ValueError is raised.
    self.assertEquals(int(obj.b), 1)
    self.assertEquals(float(obj.b), 1.0)
    self.assertEquals(int(obj.i), 7)
    self.assertEquals(float(obj.i), 7.0)
    self.assertEquals(int(obj.f), 3)
    self.assertEquals(float(obj.f), 3.14)
    self.assertEquals(int(obj.s), 5)
    self.assertEquals(float(obj.s), 5.0)
    self.assertEquals(int(obj.u), 2)
    self.assertEquals(float(obj.u), 2.0)

  def testTriggers(self):
    obj = TriggerObject()
    self.assertEquals(obj.xval, 7)
    self.assertEquals(obj.triggers, 0)

    obj.val = 99
    self.assertEquals(obj.xval, 99)
    self.assertEquals(obj.val, 99)
    self.assertEquals(obj.triggers, 1)
    obj.val = 99
    self.assertEquals(obj.triggers, 1)
    obj.val = 98
    self.assertEquals(obj.triggers, 2)

    obj.a = 5
    self.assertEquals(obj.triggers, 3)
    obj.a = '5'
    self.assertEquals(obj.triggers, 4)
    obj.a = '5'
    self.assertEquals(obj.triggers, 4)

    obj.b = 0
    self.assertEquals(obj.triggers, 5)
    obj.b = '0'
    self.assertEquals(obj.triggers, 5)
    obj.b = 'TRuE'
    self.assertEquals(obj.b, 1)
    self.assertEquals(obj.triggers, 6)

    # test that exceptions get passed through
    obj.i = 9
    self.assertEquals(obj.triggers, 7)
    self.assertRaises(ValueError, setattr, obj, 'i', '1.2')
    self.assertEquals(obj.triggers, 7)

    # test that validators get passed through, and triggering check happens
    # *after* validation.
    obj.v = 5
    self.assertEquals(obj.v, 5 + 1)
    self.assertEquals(type(obj.v), float)
    self.assertEquals(obj.triggers, 8)
    obj.v = 5
    self.assertEquals(obj.triggers, 8)

    obj.vv = 12
    self.assertEquals(obj.vv, 2 * 12)
    self.assertEquals(type(obj.vv), float)
    self.assertEquals(obj.triggers, 9)
    obj.vv = 12
    self.assertEquals(obj.triggers, 9)

    obj.m = '00:11:22:33:44:66'
    self.assertEquals(obj.triggers, 10)

    obj.ip4 = '3.4.5.6'
    self.assertEquals(obj.triggers, 11)

    obj.ip6 = '3333::'
    self.assertEquals(obj.triggers, 12)

  def testReadOnly(self):
    obj = ReadOnlyObject()
    obj2 = ReadOnlyObject()
    self.assertRaises(AttributeError, setattr, obj, 'b', True)
    self.assertRaises(AttributeError, setattr, obj, 'b', False)
    self.assertEquals(obj.b, True)
    self.assertEquals(obj2.b, True)
    type(obj).b.Set(obj, False)
    self.assertEquals(obj.b, False)
    self.assertEquals(obj2.b, True)

    self.assertEquals(obj.d, datetime.datetime(1970, 1, 1, 0, 0))
    type(obj).d.Set(obj, 1367765220.0)
    self.assertEquals(obj.d, datetime.datetime(2013, 5, 5, 14, 47))
    self.assertEquals(obj.i, 5)
    type(obj).i.Set(obj, 6)
    self.assertEquals(obj.i, 6)
    self.assertEquals(obj.s, 'foo')
    type(obj).s.Set(obj, 'bar')
    self.assertEquals(obj.s, 'bar')
    self.assertEquals(obj.e, None)
    type(obj).e.Set(obj, 'x')
    self.assertEquals(obj.e, 'x')
    self.assertRaises(AttributeError, setattr, obj, 'i', 5)
    self.assertRaises(AttributeError, setattr, obj, 'd', 0.0)
    self.assertRaises(AttributeError, setattr, obj, 's', 'foo')
    self.assertRaises(AttributeError, setattr, obj, 'e', None)
    self.assertRaises(AttributeError, setattr, obj, 'm', '00:11:22:44:55:66')
    self.assertRaises(AttributeError, setattr, obj, 'ip4', '9.8.7.6')
    self.assertRaises(AttributeError, setattr, obj, 'ip6', '4444::')

  def testReallyBigInteger(self):
    obj = ReadOnlyObject()
    obj2 = TestObject()
    type(obj).i.Set(self, long(30595169952))
    type(obj).u.Set(self, long(30595169952))
    obj2.i = long(30595169952L)
    obj2.u = long(30595169952L)

  def testNotifications(self):
    obj = NotifierTestObject()
    obj1 = NotifierTestObject()
    tr.cwmptypes.AddNotifier(type(obj), 'a', ChangeValues)
    tr.cwmptypes.AddNotifier(type(obj1), 'a', ChangeValues)
    self.assertNotEqual(obj.a, obj.b)
    obj.b = 7
    self.assertEquals(obj.a, 0)
    self.assertEquals(obj.b, 7)
    self.assertEquals(obj1.a, 0)
    self.assertEquals(obj1.b, 5)
    obj.a = 10
    self.assertEquals(obj.a, obj.b)
    self.assertEquals(obj1.a, 0)
    self.assertEquals(obj1.b, 5)

  def testNumberOf(self):
    obj = NumberOfObject()
    obj.TestList = ['a', 'b', 'c']
    obj.TestDict = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}
    self.assertEqual(obj.TestListNumberOfEntries, 3)
    self.assertEqual(obj.TestDictNumberOfEntries, 4)
    obj.TestList.extend(['d', 'e'])
    self.assertEqual(obj.TestListNumberOfEntries, 5)

    # Make sure two objects correctly have two different counts
    obj2 = NumberOfObject()
    self.assertEqual(obj2.TestListNumberOfEntries, 0)
    self.assertEqual(obj.TestListNumberOfEntries, 5)

  def testEvilUnicode(self):
    t = TestObject()
    # This test just looks for exceptions
    t.s = 5
    t.s = u'this is a test'
    t.s = '\xf1'
    t.s = '\xfe'
    t.s = '\xff'
    # selected http://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
    t.s = '\xed\x9f\xbf'
    t.s = '\xee\x80\x80'
    t.s = '\x80'
    t.s = '\xbf'
    t.s = '\xc0\xaf'
    t.s = '\xe0\x80\xaf'
    t.s = '\xed\xa0\x80'
    t.s = '\xed\xa0\x80\xed\xb0\x80'
    t.s = '\xef\xbf\xbe'
    t.s = 'ma\xf1ana'  # ISO8859
    self.assertEqual(u'ma\ufffdana', t.s)


if __name__ == '__main__':
  unittest.main()
