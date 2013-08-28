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
import tornado.testing
import acs_config


class AcsConfigTest(tornado.testing.AsyncTestCase):
  """Tests for acs_config.py."""

  def setUp(self):
    super(AcsConfigTest, self).setUp()
    self.old_ACSCONTACT = acs_config.ACSCONTACT
    self.old_ACSCONNECTED = acs_config.ACSCONNECTED
    self.old_SET_ACS = acs_config.SET_ACS
    acs_config.SET_ACS = 'testdata/acs_config/set-acs'
    self.scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = self.scriptout.name

  def tearDown(self):
    super(AcsConfigTest, self).tearDown()
    acs_config.ACSCONTACT = self.old_ACSCONTACT
    acs_config.ACSCONNECTED = self.old_ACSCONNECTED
    acs_config.SET_ACS = self.old_SET_ACS
    self.scriptout = None  # File will delete itself

  def testSetAcs(self):
    ac = acs_config.AcsConfig()
    self.assertEqual(ac.GetAcsUrl(), 'bar')
    ac.SetAcsUrl('foo')
    self.assertEqual(self.scriptout.read().strip(), 'cwmp foo')

  def testClearAcs(self):
    ac = acs_config.AcsConfig()
    ac.SetAcsUrl('')
    self.assertEqual(self.scriptout.read().strip(), 'cwmp clear')

  def testAcsAccess(self):
    tmpdir = tempfile.mkdtemp()
    acscontact = os.path.join(tmpdir, 'acscontact')
    self.assertRaises(OSError, os.stat, acscontact)  # File does not exist yet
    acs_config.ACSCONTACT = acscontact
    acsconnected = os.path.join(tmpdir, 'acsconnected')
    self.assertRaises(OSError, os.stat, acsconnected)
    acs_config.ACSCONNECTED = acsconnected
    ac = acs_config.AcsConfig()

    acsurl = 'this is the acs url'

    # Simulate ACS connection attempt
    ac.AcsAccessAttempt(acsurl)
    self.assertTrue(os.stat(acscontact))
    self.assertEqual(open(acscontact, 'r').read(), acsurl)
    self.assertRaises(OSError, os.stat, acsconnected)

    # Simulate ACS connection success
    ac.AcsAccessSuccess(acsurl)
    self.assertTrue(os.stat(acscontact))
    self.assertTrue(os.stat(acsconnected))
    self.assertEqual(open(acsconnected, 'r').read(), acsurl)

    # cleanup
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
  unittest.main()
