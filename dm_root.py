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
"""The Device Model root, allowing specific platforms to populate it."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import os.path
import sys
import google3
import dm.catawampus
import dm.management_server
import tr.core
import tr.handle


def _RecursiveImport(name):
  return __import__(name, fromlist=[''])


class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform, ext_dir):
    tr.core.Exporter.__init__(self)
    if platform:
      self.device = _RecursiveImport('platform.%s.device' % platform)
      (params, objects) = self.device.PlatformInit(name=platform,
                                                   device_model_root=self)
    else:
      (params, objects) = (list(), list())
    self.X_CATAWAMPUS_ORG_CATAWAMPUS = dm.catawampus.CatawampusDm()
    objects.append('X_CATAWAMPUS-ORG_CATAWAMPUS')
    self.Export(params=params, objects=objects)
    if ext_dir:
      sys.path.insert(0, os.path.abspath(ext_dir))
      try:
        extpath = os.path.join(ext_dir, 'ext.py')
        if not os.path.exists(extpath):
          extpath = os.path.join(ext_dir, 'ext.pyc')
        if os.path.exists(extpath):
          print 'Importing base extension: %r' % extpath
          extmod = _RecursiveImport('ext')
          extmod.Extend(self)
        for extpath in (glob.glob(os.path.join(ext_dir, '*/ext.py'))
                        + glob.glob(os.path.join(ext_dir, '*/ext.pyc'))):
          print 'Importing extension: %r' % extpath
          extname = os.path.split(os.path.split(extpath)[0])[1]
          extmod = _RecursiveImport(extname + '.ext')
          extmod.Extend(self)
      finally:
        sys.path.pop(0)

  def get_platform_config(self, ioloop):
    """Return the platform_config.py object for this platform."""
    return self.device.PlatformConfig(ioloop=ioloop)

  def add_management_server(self, mgmt):
    try:
      ms181 = self.Device
    except AttributeError:
      pass  # no tr-181 is available for this platform
    else:
      ms181.ManagementServer = dm.management_server.ManagementServer181(mgmt)

    try:
      ms98 = self.InternetGatewayDevice
    except AttributeError:
      pass  # no tr-098 is available for this platform
    else:
      ms98.ManagementServer = dm.management_server.ManagementServer98(mgmt)

  def configure_tr157(self, cpe):
    """Adds the cpe and root objects to the tr157 periodic stat object."""
    try:
      tr157_object = self.InternetGatewayDevice.PeriodicStatistics
    except AttributeError:
      pass  # no tr-157 object on the InternetGatewayDevice.
    else:
      tr157_object.SetCpe(cpe)
      tr157_object.SetRoot(tr.handle.Handle(self))

    try:
      tr157_object = self.Device.PeriodicStatistics
    except AttributeError:
      pass  # no tr-157 object found on the Device object
    else:
      tr157_object.SetCpe(cpe)
      tr157_object.SetRoot(tr.handle.Handle(self))
