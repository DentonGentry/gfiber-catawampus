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
import dm.bluetooth
import dm.catawampus
import dm.gfibertv
import dm.glaukus
import dm.gvsb
import dm.hat
import dm.inadyn
import dm.ip_diag_http
import dm.ip_diag_ping
import dm.isostream
import dm.management_server
import dm.ookla
import dm.selftest
import dm.wifiblaster
import tr.core
import tr.experiment

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0


def _RecursiveImport(name):
  return __import__(name, fromlist=[''])


class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform, ext_dir):
    tr.core.Exporter.__init__(self)
    self.handle = tr.experiment.ExperimentHandle(self)
    if platform:
      self.device = _RecursiveImport('platform.%s.device' % platform)
      (params, objects) = self.device.PlatformInit(name=platform,
                                                   device_model_root=self)
    else:
      (params, objects) = (list(), list())
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

  def add_cwmp_extensions(self):
    try:
      dev = self.Device
    except AttributeError:
      print 'add_cwmp_extensions: no tr-181 Device model available.'
      return  # no tr-181 is available for this platform
    dev.Export(objects=['X_CATAWAMPUS-ORG'])
    cata = dev.X_CATAWAMPUS_ORG = tr.core.Extensible(
        BASE.Device.X_CATAWAMPUS_ORG)()
    cata.Bluetooth = dm.bluetooth.Bluetooth()
    cata.Catawampus = dm.catawampus.CatawampusDm(self.handle)
    cata.DynamicDNS = dm.inadyn.Inadyn()
    # TODO(apenwarr): remove deprecated Catawapus.Experiments eventually.
    #   then we'll just have cata.Experiments and construct it here instead.
    #   Experiments are new, but so is the Device.X_CATAWAMPUS_ORG object.
    #   For now, we don't assume that one will be supported by ACS.
    cata.Experiments = cata.Catawampus.Experiments
    cata.GFiberTV = dm.gfibertv.GFiberTv(
        mailbox_url='http://localhost:51834/xmlrpc',
        my_serial=self.device.DeviceId().SerialNumber)
    cata.Glaukus = dm.glaukus.Glaukus()
    cata.GVSB = dm.gvsb.Gvsb()
    cata.HAT = dm.hat.Hat()
    cata.HttpDownload = dm.ip_diag_http.DiagHttpDownload()
    cata.Isostream = dm.isostream.Isostream()
    cata.Ping = dm.ip_diag_ping.DiagPing()
    cata.SelfTest = dm.selftest.SelfTest()
    cata.Speedtest = dm.ookla.Speedtest()
    cata.Wifiblaster = dm.wifiblaster.Wifiblaster()
    self.handle.root_experiments = cata.Catawampus.Experiments

    # TODO(apenwarr): Legacy names. Delete after the ACS stops using these.
    #   Other than a few places where we added only individual parameters
    #   to existing objects, we're trying to clean up our extensions by
    #   centralizing them in a single extension section under Device.
    #   Technically it may be incorrect to have more than one root-
    #   level object, so although it's necessary to have both Device
    #   and InternetGatewayDevice (for simultaneous tr-098 and tr-181 support)
    #   we shouldn't make it worse by adding our own.  But we did that for
    #   a while, so we need some temporary backward compatibility.
    cata.GFiberTV.Export(objects=['SelfTest'])
    cata.GFiberTV.SelfTest = cata.SelfTest

    if isinstance(self.Device.IP.Diagnostics, tr.core.Exporter):
      self.Device.IP.Diagnostics.Export(objects=[
          'X_CATAWAMPUS-ORG_Speedtest',
          'X_CATAWAMPUS-ORG_Isostream',
          'X_CATAWAMPUS-ORG_HttpDownload',
      ])
    self.Device.IP.Diagnostics.X_CATAWAMPUS_ORG_Speedtest = cata.Speedtest
    self.Device.IP.Diagnostics.X_CATAWAMPUS_ORG_Isostream = cata.Isostream
    self.Device.IP.Diagnostics.X_CATAWAMPUS_ORG_HttpDownload = cata.HttpDownload

    # TODO(apenwarr): remove these aliases once we're sure nobody uses them.
    #  They're deprecated.  Use Device.X_CATAWAMPUS-ORG.Whatever instead.
    self.Device.Export(objects=['X_CATAWAMPUS-ORG_DynamicDNS'])
    self.Device.X_CATAWAMPUS_ORG_DynamicDNS = cata.DynamicDNS
    self.Export(objects=['X_CATAWAMPUS-ORG_CATAWAMPUS',
                         'X_GOOGLE-COM_GFIBERTV',
                         'X_GOOGLE-COM_GVSB',
                         'X_GOOGLE-COM_HAT'])
    self.X_CATAWAMPUS_ORG_CATAWAMPUS = cata.Catawampus
    self.X_GOOGLE_COM_GFIBERTV = cata.GFiberTV
    self.X_GOOGLE_COM_GVSB = cata.GVSB
    self.X_GOOGLE_COM_HAT = cata.HAT

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
      tr157_object.SetRoot(self.handle)

    try:
      tr157_object = self.Device.PeriodicStatistics
    except AttributeError:
      pass  # no tr-157 object found on the Device object
    else:
      tr157_object.SetCpe(cpe)
      tr157_object.SetRoot(self.handle)
