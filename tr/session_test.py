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

# unittest requires method names starting in 'test'
# pylint: disable=invalid-name

"""Unit tests for session.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import time
from wvtest import unittest

import google3
import session


class CwmpSessionTest(unittest.TestCase):
  """tests for CwmpSession."""

  def testStateConnect(self):
    cs = session.CwmpSession('')

    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    # should be no change
    cs.state_update(on_hold=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    # transition to ACTIVE
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testActive(self):
    cs = session.CwmpSession('')
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # should be no change
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to ONHOLD
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition back to ACTIVE
    cs.state_update(on_hold=False)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to NOMORE
    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testOnHold(self):
    cs = session.CwmpSession('')
    cs.state_update(sent_inform=True)
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # No change
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # back to ACTIVE
    cs.state_update(on_hold=False)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testNoMore(self):
    cs = session.CwmpSession('')

    # transition to NOMORE
    cs.state_update(sent_inform=True)
    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # should be no change
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to DONE
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

  def testDone(self):
    cs = session.CwmpSession('')
    cs.state_update(sent_inform=True)
    cs.state_update(cpe_to_acs_empty=True)
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())


class SimpleCacheObject(object):

  def __init__(self):
    self.cache_this_function_n = 0
    self.cache_this_function_args_n = 0

  @session.cache
  def cache_this_function(self):
    self.cache_this_function_n += 1

  @session.cache
  def cache_function_with_args(
      self, arg1, arg2, x=0, y=0):  # pylint: disable=unused-argument
    self.cache_this_function_args_n += 1 + x + y


@session.cache
def SimpleCacheFunction():
  return time.time()


cache_iter_start = 1


def _CacheIterFunction():
  global cache_iter_start
  yield cache_iter_start
  cache_iter_start += 1
  yield cache_iter_start
  cache_iter_start += 1


@session.cache
def CacheIterFunction():
  return _CacheIterFunction()


@session.cache
def CacheListFunction():
  return list(_CacheIterFunction())


@session.cache_as_list
def CacheAsListFunction():
  return _CacheIterFunction()


class SessionCacheTest(unittest.TestCase):
  """tests for SessionCache."""

  def testCacheObject(self):
    t1 = SimpleCacheObject()
    t2 = SimpleCacheObject()
    t3 = SimpleCacheObject()
    for _ in range(1001):
      t1.cache_this_function()
      t2.cache_this_function()
      t3.cache_this_function()
    self.assertEqual(t1.cache_this_function_n, 1)
    self.assertEqual(t2.cache_this_function_n, 1)
    self.assertEqual(t3.cache_this_function_n, 1)
    session.cache.flush()
    for _ in range(101):
      t1.cache_this_function()
      t2.cache_this_function()
    self.assertEqual(t1.cache_this_function_n, 2)
    self.assertEqual(t2.cache_this_function_n, 2)
    self.assertEqual(t3.cache_this_function_n, 1)

  def testCacheFunction(self):
    t = SimpleCacheFunction()
    for _ in range(1000):
      self.assertEqual(t, SimpleCacheFunction())
    session.cache.flush()
    self.assertNotEqual(t, SimpleCacheFunction())

  def testCacheFunctionArgs(self):
    t = SimpleCacheObject()
    for i in range(100):
      t.cache_function_with_args(i, 0)
    self.assertEqual(t.cache_this_function_args_n, 100)

  def testCacheFunctionComplicatedArgs(self):
    t = SimpleCacheObject()
    arg = [1, 2, [3, 4], [5, 6, [7, 8, [9, 10]]], 11, 12]
    for i in range(10):
      t.cache_function_with_args(i, arg, x=5, y=7)
    self.assertEqual(t.cache_this_function_args_n,
                     10 * (1 + 5 + 7))
    for i in range(10):
      t.cache_function_with_args(i, arg, x=5, y=7)
      t.cache_function_with_args(99, arg)
      t.cache_function_with_args(99, arg, y=9)
    self.assertEqual(t.cache_this_function_args_n,
                     10 * (1 + 5 + 7) +
                     1 + (1 + 9))

  def testCacheIterFunction(self):
    self.assertRaises(TypeError, CacheIterFunction)
    self.assertEqual(CacheListFunction(), CacheListFunction())
    self.assertEqual(list(CacheListFunction()), CacheListFunction())
    self.assertEqual(len(CacheListFunction()), 2)

    self.assertEqual(CacheAsListFunction(), CacheAsListFunction())
    self.assertEqual(list(CacheAsListFunction()), CacheAsListFunction())
    self.assertEqual(len(CacheAsListFunction()), 2)

    self.assertEqual(CacheListFunction(), [1, 2])
    self.assertEqual(CacheAsListFunction(), [3, 4])


RunAtEndTestResults = {}


@session.RunAtEnd
def setBarAtEnd(val):
  RunAtEndTestResults['bar'] = val


class RunAtEndTest(unittest.TestCase):

  def setUp(self):
    RunAtEndTestResults.clear()

  @session.RunAtEnd
  def setFooAtEnd(self, val):
    RunAtEndTestResults['foo'] = val

  def testRunAtEnd(self):
    self.setFooAtEnd(1)
    setBarAtEnd(2)
    self.assertEqual(len(RunAtEndTestResults), 0)
    session._RunAtEnd.runall()
    self.assertEqual(len(RunAtEndTestResults), 2)
    self.assertEqual(RunAtEndTestResults['foo'], 1)
    self.assertEqual(RunAtEndTestResults['bar'], 2)


if __name__ == '__main__':
  unittest.main()
