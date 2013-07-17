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

# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409
#
# Refactored, originally from: platform/gfmedia/device_test.py

"""Unit tests for device.py."""

__author__ = 'jnewlin@google.com (John Newlin)'

import os
import shutil
import tempfile
import unittest

import google3
import tornado.ioloop
import tornado.testing
import acs_config


class MockIoloop(object):
  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, unused_monotonic=None):
    self.timeout = timeout
    self.callback = callback


class AcsConfigTest(tornado.testing.AsyncTestCase):
  """Tests for acs_config.py."""

  def setUp(self):
    super(AcsConfigTest, self).setUp()
    self.old_ACSCONNECTED = acs_config.ACSCONNECTED
    self.old_SET_ACS = acs_config.SET_ACS

  def tearDown(self):
    super(AcsConfigTest, self).tearDown()
    acs_config.ACSCONNECTED = self.old_ACSCONNECTED
    acs_config.SET_ACS = self.old_SET_ACS

  def testSetAcs(self):
    acs_config.SET_ACS = 'testdata/acs_config/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    ac = acs_config.AcsConfig(ioloop=MockIoloop())
    self.assertEqual(ac.GetAcsUrl(), 'bar')
    ac.SetAcsUrl('foo')
    self.assertEqual(scriptout.read().strip(), 'cwmp foo')

  def testClearAcs(self):
    acs_config.SET_ACS = 'testdata/acs_config/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    ac = acs_config.AcsConfig(ioloop=MockIoloop())
    ac.SetAcsUrl('')
    self.assertEqual(scriptout.read().strip(), 'cwmp clear')

  def testAcsAccess(self):
    acs_config.SET_ACS = 'testdata/acs_config/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    ioloop = MockIoloop()
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, 'acsconnected')
    self.assertRaises(OSError, os.stat, tmpfile)  # File does not exist yet
    acs_config.ACSCONNECTED = tmpfile
    ac = acs_config.AcsConfig(ioloop)
    acsurl = 'this is the acs url'

    # Simulate ACS connection
    ac.AcsAccessAttempt(acsurl)
    ac.AcsAccessSuccess(acsurl)
    self.assertTrue(os.stat(tmpfile))
    self.assertEqual(open(tmpfile, 'r').read(), acsurl)
    self.assertTrue(ioloop.timeout)
    self.assertTrue(ioloop.callback)

    # Simulate timeout
    ac.AcsAccessAttempt(acsurl)
    scriptout.truncate()
    ioloop.callback()
    self.assertRaises(OSError, os.stat, tmpfile)
    self.assertEqual(scriptout.read().strip(), 'timeout ' + acsurl)

    # cleanup
    shutil.rmtree(tmpdir)

  def testGetAcsUrlTimeout(self):
    acs_config.TIMEOUTFILE = 'testdata/acs_config/garbage'
    ac = acs_config.AcsConfig(ioloop=MockIoloop())
    self.assertEqual(ac.ACSTimeout('/no_such_file_at_this_path', 60), 60)
    self.assertEqual(ac.ACSTimeout('testdata/acs_config/garbage', 60), 60)
    self.assertEqual(ac.ACSTimeout('testdata/acs_config/timeout', 60), 120)


if __name__ == '__main__':
  unittest.main()
