#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TR-069 has mandatory attribute names that don't comply with policy
# pylint: disable-msg=C6409

"""Implementation of Device.CaptivePortal hierarchy of objects.
"""

__author__ = 'estrulyov@google.com (Eugene Strulyov)'

import subprocess
import tr.helpers
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

CATA181DEV = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181_CAPTIVE_PORTAL = CATA181DEV.Device.CaptivePortal

CAPTIVE_PORTAL = 'captive_portal'


class CaptivePortal(CATA181_CAPTIVE_PORTAL):
  """Device.CaptivePortal."""

  AllowedList = tr.cwmptypes.TriggerString('')
  Enable = tr.cwmptypes.TriggerBool(False)
  URL = tr.cwmptypes.TriggerString('')
  X_CATAWAMPUS_ORG_Port = tr.cwmptypes.TriggerUnsigned(0)

  def __init__(self):
    super(CaptivePortal, self).__init__()
    self._interfaces = ['wlan0_portal']

  @property
  def Status(self):
    """Return status of this entry."""

    if not self.Enable:
      return 'Disabled'
    elif not self.X_CATAWAMPUS_ORG_Port:
      return 'X_CATAWAMPUS_ORG_Error_PortNotSet'
    elif not self.URL:
      return 'Error_URLEmpty'
    else:
      return 'Enabled'

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    if (self.Enable and self.URL and self.X_CATAWAMPUS_ORG_Port
        and self.AllowedList):
      args = [CAPTIVE_PORTAL, 'start', '-p', str(self.X_CATAWAMPUS_ORG_Port),
              '-i', ' '.join(self._interfaces), '-a', str(self.AllowedList)]
    else:
      args = [CAPTIVE_PORTAL, 'stop']
    self._runCmd(args)
    # TODO(estrulyov): also start/stop HTTP bouncer

  def _runCmd(self, args):
    print args
    subprocess.call(args, shell=False)

