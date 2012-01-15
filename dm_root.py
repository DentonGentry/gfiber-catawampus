#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""The Device Model root, allowing specific platforms to populate it."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import dm.catawampus
import dm.management_server
import imp
import os.path
import traceroute
import tr.core

PLATFORMDIR = "platform"

class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform):
    tr.core.Exporter.__init__(self)
    if platform:
      path = os.path.join(PLATFORMDIR, platform, 'device.py')
      device = imp.load_source('device', path)
      (params, objects) = device.PlatformInit(name=platform,
                                              device_model_root=self)
    else:
      (params, objects) = (list(), list())
    self.TraceRoute = traceroute.TraceRoute(loop)
    objects.append('TraceRoute')
    self.X_CATAWAMPUS_ORG_CATAWAMPUS = dm.catawampus.CatawampusDm()
    objects.append('X_CATAWAMPUS-ORG_CATAWAMPUS')
    self.Export(params=params, objects=objects)

  def add_management_server(self, mgmt):
    # tr-181 Device.ManagementServer
    try:
      ms181 = self.GetExport('Device')
      ms181.ManagementServer = dm.management_server.ManagementServer181(mgmt)
    except AttributeError:
      pass  # no tr-181 for this platform

    # tr-98 InternetGatewayDevice.ManagementServer
    try:
      ms98 = self.GetExport('InternetGatewayDevice')
      ms98.ManagementServer = dm.management_server.ManagementServer98(mgmt)
    except AttributeError:
      pass  # no tr-98 for this platform
