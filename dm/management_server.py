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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name

"""Implementation of tr-181 Device.ManagementServer hierarchy of objects.

Handles the Device.ManagementServer portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.tr098_v1_4
import tr.tr181_v2_2
import tr.cwmptypes


BASEMGMT181 = tr.tr181_v2_2.Device_v2_2.Device.ManagementServer
BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
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
    super(ManagementServer181, self).__init__()
    self.mgmt = mgmt

    self.Unexport(['DownloadProgressURL', 'KickURL', 'NATDetected',
                   'STUNMaximumKeepAlivePeriod', 'STUNMinimumKeepAlivePeriod',
                   'STUNPassword', 'STUNServerAddress', 'STUNServerPort',
                   'STUNUsername', 'UDPConnectionRequestAddress'])

    self.ManageableDeviceList = {}

  def StartTransaction(self):
    self.mgmt.StartTransaction()

  def AbandonTransaction(self):
    self.mgmt.AbandonTransaction()

  def CommitTransaction(self):
    self.mgmt.CommitTransaction()

  @property
  def ManageableDeviceNumberOfEntries(self):
    return len(self.ManageableDeviceList)

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
      raise KeyError('No such attribute %s' % name)

  def __setattr__(self, name, value):
    if name in self.MGMTATTRS:
      setattr(self.mgmt, name, value)
    else:
      BASEMGMT181.__setattr__(self, name, value)

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
    super(ManagementServer98, self).__init__()
    self.mgmt = mgmt
    self.Unexport(['AliasBasedAddressing', 'AutoCreateInstances',
                   'DownloadProgressURL', 'InstanceMode', 'KickURL',
                   'ManageableDeviceNotificationLimit', 'NATDetected',
                   'STUNEnable', 'STUNMaximumKeepAlivePeriod',
                   'STUNMinimumKeepAlivePeriod', 'STUNPassword',
                   'STUNServerAddress', 'STUNServerPort', 'STUNUsername',
                   'UDPConnectionRequestAddress',
                   'UDPConnectionRequestAddressNotificationLimit'])

    self.EmbeddedDeviceList = {}
    self.ManageableDeviceList = {}
    self.VirtualDeviceList = {}

  def StartTransaction(self):
    self.mgmt.StartTransaction()

  def AbandonTransaction(self):
    self.mgmt.AbandonTransaction()

  def CommitTransaction(self):
    self.mgmt.CommitTransaction()

  @property
  def EmbeddedDeviceNumberOfEntries(self):
    return len(self.EmbeddedDeviceList)

  @property
  def ManageableDeviceNumberOfEntries(self):
    return len(self.ManageableDeviceList)

  @property
  def STUNEnable(self):
    return False

  @property
  def UpgradesManaged(self):
    return True

  @property
  def VirtualDeviceNumberOfEntries(self):
    return len(self.VirtualDeviceList)

  def __getattr__(self, name):
    if name in self.MGMTATTRS:
      return getattr(self.mgmt, name)
    else:
      raise KeyError('No such attribute %s' % name)

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
