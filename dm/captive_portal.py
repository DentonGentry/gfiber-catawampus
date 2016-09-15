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
# pylint:disable=invalid-name

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
  X_CATAWAMPUS_ORG_AuthorizerURL = tr.cwmptypes.TriggerString('')
  X_CATAWAMPUS_ORG_ExtraTLSHosts = tr.cwmptypes.TriggerString(
      '*.gfsvc.com fonts.googleapis.com fonts.gstatic.com')

  def __init__(self):
    super(CaptivePortal, self).__init__()

  @property
  def Status(self):
    """Return status of this entry."""

    if not self.Enable:
      return 'Disabled'
    elif not self.URL:
      return 'Error_URLEmpty'
    else:
      return 'Enabled'

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    if self.Enable and self.URL:
      args = [CAPTIVE_PORTAL, 'start', '-u', self.URL]
      if self.AllowedList:
        args += ['-a', self.AllowedList]
      if self.X_CATAWAMPUS_ORG_AuthorizerURL:
        args += ['-A', self.X_CATAWAMPUS_ORG_AuthorizerURL]
      if self.X_CATAWAMPUS_ORG_ExtraTLSHosts:
        args += ['-e', self.X_CATAWAMPUS_ORG_ExtraTLSHosts]
    else:
      args = [CAPTIVE_PORTAL, 'stop']
    self._runCmd(args)

  def _runCmd(self, args):
    print args
    subprocess.call(args, shell=False)

