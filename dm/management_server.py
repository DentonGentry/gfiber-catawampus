#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.ManagementServer hierarchy of objects.

Handles the Device.ManagementServer portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.core
import tr.tr098_v1_2
import tr.tr181_v2_2

BASEMGMT181 = tr.tr181_v2_2.Device_v2_2.Device.ManagementServer
BASE98IGD = tr.tr098_v1_2.InternetGatewayDevice_v1_4.InternetGatewayDevice
BASEMGMT98 = BASE98IGD.ManagementServer


class ManagementServer181(BASEMGMT181):
  """Implementation of tr-181 Device.ManagementServer."""

  MGMTATTRS = frozenset([
      'CWMPRetryIntervalMultiplier', 'CWMPRetryMinimumWaitInterval',
      'ConnectionRequestPassword', 'ConnectionRequestURL',
      'ConnectionRequestUsername', 'DefaultActiveNotificationThrottle',
      'EnableCWMP', 'ParameterKey', 'Password', 'PeriodicInformEnable',
      'PeriodicInformInterval', 'PeriodicInformTime', 'URL', 'Username'])

  def __init__(self, mgmt):
    """Proxy object for tr-181 ManagementServer support.

    All requests for active, supported parameters pass through to the
    underlying management server implementation.

    Args:
      mgmt: the real management configuration object.
    """
    BASEMGMT181.__init__(self)
    self.mgmt = mgmt

    self.Unexport('DownloadProgressURL')
    self.Unexport('KickURL')
    self.Unexport('NATDetected')
    self.Unexport('STUNMaximumKeepAlivePeriod')
    self.Unexport('STUNMinimumKeepAlivePeriod')
    self.Unexport('STUNPassword')
    self.Unexport('STUNServerAddress')
    self.Unexport('STUNServerPort')
    self.Unexport('STUNUsername')
    self.Unexport('UDPConnectionRequestAddress')

    self.ManageableDeviceList = {}
    self.ManageableDeviceNumberOfEntries = 0

  @property
  def STUNEnable(self):
    return False

  @property
  def UpgradesManaged(self):
    return True

  def __getattr__(self, name):
    if name in self.MGMTATTRS:
      return getattr(self.mgmt, name)
    else:
      raise AttributeError

  def __setattr__(self, name, value):
    if name in self.MGMTATTRS:
      return setattr(self.mgmt, name, value)
    else:
      return BASEMGMT181.__setattr__(self, name, value)

  def __delattr__(self, name):
    if name in self.MGMTATTRS:
      return delattr(self.mgmt, name)
    else:
      return BASEMGMT181.__delattr__(self, name)


class ManagementServer98(BASEMGMT98):
  """Implementation of tr-98 InternetGatewayDevice.ManagementServer."""

  MGMTATTRS = frozenset([
      'CWMPRetryIntervalMultiplier', 'CWMPRetryMinimumWaitInterval',
      'ConnectionRequestPassword', 'ConnectionRequestURL',
      'ConnectionRequestUsername', 'DefaultActiveNotificationThrottle',
      'EnableCWMP', 'ParameterKey', 'Password', 'PeriodicInformEnable',
      'PeriodicInformInterval', 'PeriodicInformTime', 'URL', 'Username'])

  def __init__(self, mgmt):
    """Proxy object for tr-98 ManagementServer support.

    All requests for active, supported parameters pass through to the
    underlying management server implementation.

    Args:
      mgmt: the real management configuration object.
    """
    BASEMGMT98.__init__(self)
    self.mgmt = mgmt
    self.Unexport('DownloadProgressURL')
    self.Unexport('KickURL')
    self.Unexport('UDPConnectionRequestAddress')

    self.ManageableDeviceList = {}
    self.ManageableDeviceNumberOfEntries = 0

  @property
  def UpgradesManaged(self):
    return True

  def __getattr__(self, name):
    if name in self.MGMTATTRS:
      return getattr(self.mgmt, name)
    else:
      raise AttributeError

  def __setattr__(self, name, value):
    if name in self.MGMTATTRS:
      return setattr(self.mgmt, name, value)
    else:
      return BASEMGMT98.__setattr__(self, name, value)

  def __delattr__(self, name):
    if name in self.MGMTATTRS:
      return delattr(self.mgmt, name)
    else:
      return BASEMGMT98.__delattr__(self, name)


def main():
  pass

if __name__ == '__main__':
  main()
