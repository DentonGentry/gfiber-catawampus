#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""The Device Model root, allowing specific platforms to populate it."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import dm.catawampus
import dm.management_server
import tr.core
import traceroute


def _RecursiveImport(name):
  return __import__(name, fromlist=[''])


class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform):
    tr.core.Exporter.__init__(self)
    if platform:
      self.device = _RecursiveImport('platform.%s.device' % platform)
      (params, objects) = self.device.PlatformInit(name=platform,
                                                   device_model_root=self)
    else:
      (params, objects) = (list(), list())
    self.TraceRoute = traceroute.TraceRoute(loop)
    objects.append('TraceRoute')
    self.X_CATAWAMPUS_ORG_CATAWAMPUS = dm.catawampus.CatawampusDm()
    objects.append('X_CATAWAMPUS-ORG_CATAWAMPUS')
    self.Export(params=params, objects=objects)

  def get_platform_config(self):
    """Return the platform_config.py object for this platform."""
    return self.device.PlatformConfig()

  def add_management_server(self, mgmt):
    # tr-181 Device.ManagementServer
    try:
      ms181 = self.GetExport('Device')
      ms181.ManagementServer = dm.management_server.ManagementServer181(mgmt)
    except (AttributeError, KeyError):
      pass  # no tr-181 for this platform

    # tr-98 InternetGatewayDevice.ManagementServer
    try:
      ms98 = self.GetExport('InternetGatewayDevice')
      ms98.ManagementServer = dm.management_server.ManagementServer98(mgmt)
    except (AttributeError, KeyError):
      pass  # no tr-98 for this platform
