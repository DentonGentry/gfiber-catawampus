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
# pylint:disable=invalid-name

"""Implementation of tr-181 Device.UPnP hierarchy of objects.

Handles the Device.UPnP portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-6-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import subprocess
import tr.helpers
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

BASEUPNP = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.UPnP
RESTARTCMD = ['restart', 'upnpd']
UPNPFILE = '/tmp/upnpd-enabled'


class UPnP(BASEUPNP):
  """tr181 Device.UPnP object."""

  def __init__(self):
    super(UPnP, self).__init__()
    self.Unexport(objects=['Discovery', 'Description'])
    self.Device = Device()


class Device(BASEUPNP.Device):
  """tr181 Device.UPnP.Device object."""

  Enable = tr.cwmptypes.TriggerBool(False)
  UPnPDMBasicMgmt = tr.cwmptypes.ReadOnlyBool(False)
  UPnPDMConfigurationMgmt = tr.cwmptypes.ReadOnlyBool(False)
  UPnPDMSoftwareMgmt = tr.cwmptypes.ReadOnlyBool(False)
  UPnPIGD = tr.cwmptypes.TriggerBool(False)
  UPnPMediaRenderer = tr.cwmptypes.ReadOnlyBool(False)
  UPnPMediaServer = tr.cwmptypes.ReadOnlyBool(False)
  UPnPQoSDevice = tr.cwmptypes.ReadOnlyBool(False)
  UPnPQoSPolicyHolder = tr.cwmptypes.ReadOnlyBool(False)
  UPnPWLANAccessPoint = tr.cwmptypes.ReadOnlyBool(False)

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
    previous = os.path.exists(UPNPFILE)
    enable = self.Enable and self.UPnPIGD
    if previous != enable:
      self._UpdateFile(enable)
      subprocess.call(RESTARTCMD, close_fds=True)


class DeviceCapabilities(BASEUPNP.Device.Capabilities):
  """tr181 Device.UPnP.Device.Capabilities object."""

  UPnPArchitecture = tr.cwmptypes.ReadOnlyUnsigned(1)
  UPnPArchitectureMinorVer = tr.cwmptypes.ReadOnlyUnsigned(1)
  UPnPBasicDevice = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPDMBasicMgmt = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPDMConfigurationMgmt = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPDMSoftwareMgmt = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPIGD = tr.cwmptypes.ReadOnlyUnsigned(1)
  UPnPMediaRenderer = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPMediaServer = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPQoSDevice = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPQoSPolicyHolder = tr.cwmptypes.ReadOnlyUnsigned(0)
  UPnPWLANAccessPoint = tr.cwmptypes.ReadOnlyUnsigned(0)
