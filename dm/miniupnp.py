#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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
# pylint: disable-msg=C6409

"""Implementation of tr-181 Device.UPnP hierarchy of objects.

Handles the Device.UPnP portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-6-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import subprocess
import tr.helpers
import tr.types
import tr.x_catawampus_tr181_2_0

BASEUPNP = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.UPnP
UPNPFILE = '/tmp/upnpd-enabled'
RESTARTCMD = ['restart', 'upnpd']


class UPnP(BASEUPNP):
  """tr181 Device.UPnP object."""

  def __init__(self):
    super(UPnP, self).__init__()
    self.Unexport(objects=['Discovery'])
    self.Device = Device()


class Device(BASEUPNP.Device):
  """tr181 Device.UPnP.Device object."""

  Enable = tr.types.TriggerBool(False)
  UPnPDMBasicMgmt = tr.types.ReadOnlyBool(False)
  UPnPDMConfigurationMgmt = tr.types.ReadOnlyBool(False)
  UPnPDMSoftwareMgmt = tr.types.ReadOnlyBool(False)
  UPnPIGD = tr.types.TriggerBool(False)
  UPnPMediaRenderer = tr.types.ReadOnlyBool(False)
  UPnPMediaServer = tr.types.ReadOnlyBool(False)
  UPnPQoSDevice = tr.types.ReadOnlyBool(False)
  UPnPQoSPolicyHolder = tr.types.ReadOnlyBool(False)
  UPnPWLANAccessPoint = tr.types.ReadOnlyBool(False)

  def __init__(self):
    super(Device, self).__init__()
    self.Capabilities = DeviceCapabilities()
    self._UpdateFile(False)

  def _UpdateFile(self, enable):
    """Create or delete UPNPFILE."""
    if enable:
      with tr.helpers.AtomicFile(UPNPFILE) as f:
        f.write('')
    else:
      tr.helpers.Unlink(UPNPFILE)

  def Triggered(self):
    """Called at the end of the transaction to apply changes."""
    self._UpdateFile(self.Enable and self.UPnPIGD)
    subprocess.call(RESTARTCMD)


class DeviceCapabilities(BASEUPNP.Device.Capabilities):
  """tr181 Device.UPnP.Device.Capabilities object."""

  UPnPArchitecture = tr.types.ReadOnlyUnsigned(1)
  UPnPArchitectureMinorVer = tr.types.ReadOnlyUnsigned(1)
  UPnPBasicDevice = tr.types.ReadOnlyUnsigned(0)
  UPnPDMBasicMgmt = tr.types.ReadOnlyUnsigned(0)
  UPnPDMConfigurationMgmt = tr.types.ReadOnlyUnsigned(0)
  UPnPDMSoftwareMgmt = tr.types.ReadOnlyUnsigned(0)
  UPnPIGD = tr.types.ReadOnlyUnsigned(1)
  UPnPMediaRenderer = tr.types.ReadOnlyUnsigned(0)
  UPnPMediaServer = tr.types.ReadOnlyUnsigned(0)
  UPnPQoSDevice = tr.types.ReadOnlyUnsigned(0)
  UPnPQoSPolicyHolder = tr.types.ReadOnlyUnsigned(0)
  UPnPWLANAccessPoint = tr.types.ReadOnlyUnsigned(0)
