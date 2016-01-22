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
# pylint:disable=invalid-name

"""Unit tests for dm_root.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import dm_root
import os.path
import shutil
import tempfile
import tr.basemodel
import tr.experiment
import tr.cwmptypes
from tr.wvtest import unittest


BASE181 = tr.basemodel.Device
BASE98 = tr.basemodel.InternetGatewayDevice


class MockTr181(BASE181):
  pass


class MockTr98(BASE98):
  pass


class MockManagement(object):
  MostRecentURL = tr.cwmptypes.String()

  def __init__(self):
    self.EnableCWMP = False


class MockDevice(object):

  def DeviceId(self):
    class X(object):
      SerialNumber = '1234'
    return X()


class DeviceModelRootTest(unittest.TestCase):

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    self.old_ACTIVEDIR = tr.experiment.ACTIVEDIR
    tr.experiment.ACTIVEDIR = os.path.join(self.tmpdir, 'act')
    os.mkdir(tr.experiment.ACTIVEDIR)

  def tearDown(self):
    tr.experiment.ACTIVEDIR = self.old_ACTIVEDIR
    shutil.rmtree(self.tmpdir)

  def testAddManagementServer(self):
    root = dm_root.DeviceModelRoot(loop=None, platform=None,
                                   ext_dir='ext_test')
    mgmt = MockManagement()
    root.add_management_server(mgmt)  # should do nothing.

    root.device = MockDevice()
    root.Device = MockTr181()
    root.InternetGatewayDevice = MockTr98()
    root.Export(objects=['Device', 'InternetGatewayDevice'])
    root.add_cwmp_extensions()
    self.assertFalse(isinstance(root.InternetGatewayDevice.ManagementServer,
                                BASE98.ManagementServer))
    self.assertFalse(isinstance(root.Device.ManagementServer,
                                BASE181.ManagementServer))
    root.add_management_server(mgmt)  # should actually work now
    print type(root.InternetGatewayDevice.ManagementServer)
    self.assertTrue(isinstance(root.InternetGatewayDevice.ManagementServer,
                               BASE98.ManagementServer))
    print type(root.Device.ManagementServer)
    self.assertTrue(isinstance(root.Device.ManagementServer,
                               BASE181.ManagementServer))
    self.assertEqual(root.TestBaseExt, True)
    self.assertEqual(root.TestSubExt, 97)  # auto-rounded to int

    # Make sure aliasing is working as expected
    root.X_CATAWAMPUS_ORG_CATAWAMPUS.Experiments.Requested = 'test1'
    self.assertEqual(root.X_CATAWAMPUS_ORG_CATAWAMPUS.Experiments.Requested,
                     'test1')
    self.assertEqual(root.Device.X_CATAWAMPUS_ORG.Experiments.Requested,
                     'test1')
    self.assertTrue(os.path.exists(
        os.path.join(tr.experiment.ACTIVEDIR, 'test1.requested')))


if __name__ == '__main__':
  unittest.main()
