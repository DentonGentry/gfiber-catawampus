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

"""Implementation of Device.X_CATAWAMPUS-ORG_DynamicDNS hierarchy of objects.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import subprocess
import traceback
import tr.helpers
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

CATA181DEV = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181DDNS = CATA181DEV.Device.X_CATAWAMPUS_ORG_DynamicDNS
OUTPUTDIR = '/chroot/inadyn/tmp/configs'
RESTARTCMD = ['restart', 'inadyn']


class Inadyn(CATA181DDNS):
  """Device.X_CATAWAMPUS-ORG_DynamicDNS."""
  ServiceNumberOfEntries = tr.cwmptypes.NumberOf('ServiceList')

  def __init__(self):
    super(Inadyn, self).__init__()
    self.ServiceList = {}

  def Service(self):
    return Service(parent=self)

  @tr.mainloop.WaitUntilIdle
  def WriteConfigs(self):
    """Write out configs for inadyn."""
    print 'Writing inadyn configs'
    try:
      shutil.rmtree(path=OUTPUTDIR, ignore_errors=True)
      os.makedirs(OUTPUTDIR, mode=0755)
    except OSError:
      print 'Unable to create %s' % OUTPUTDIR
      return

    try:
      for (idx, service) in self.ServiceList.iteritems():
        service.WriteConfig(idx=idx)
      subprocess.check_call(RESTARTCMD, close_fds=True)
    except (IOError, OSError, subprocess.CalledProcessError):
      print 'Unable to update inadyn\n'
      traceback.print_exc()


class Service(CATA181DDNS.Service):
  """Device.X_CATAWAMPUS-ORG_DynamicDNS.Service."""

  Domain = tr.cwmptypes.TriggerString('')
  Enable = tr.cwmptypes.TriggerBool(False)
  Password = tr.cwmptypes.TriggerString('')
  ServiceName = tr.cwmptypes.TriggerString('')
  ServiceURL = tr.cwmptypes.TriggerString('')
  UpdateFrequency = tr.cwmptypes.TriggerUnsigned(1)
  Username = tr.cwmptypes.TriggerString('')

  def __init__(self, parent):
    super(Service, self).__init__()
    self.parent = parent

  def Triggered(self):
    self.parent.WriteConfigs()

  @property
  def Status(self):
    """Return status of this entry."""
    if not self.Enable:
      return 'Disabled'
    if not self.ServiceName and not self.ServiceURL:
      return 'Misconfigured_NoService'
    if not self.Domain:
      return 'Misconfigured_NoDomain'
    return 'Enabled'

  def WriteConfig(self, idx):
    """Write out the configuration for this inadyn instance.

    Args:
      idx: the {i} in Device.X_CATAWAMPUS-ORG_DynamicDNS.Service.{i}
    """
    if self.Status != 'Enabled':
      return

    filename = os.path.join(OUTPUTDIR, 'inadyn.' + str(idx) + '.conf')
    with tr.helpers.AtomicFile(filename) as f:
      f.write('system ' + self.ServiceName + '\n')
      if self.ServiceURL:
        f.write('dyndns_server_url ' + self.ServiceURL + '\n')
      if self.Username:
        f.write('username ' + self.Username + '\n')
      if self.Password:
        f.write('password ' + self.Password + '\n')
      f.write('update_period_sec ' + str(self.UpdateFrequency * 60) + '\n')
      for alias in self.Domain.split(','):
        f.write('alias ' + alias + '\n')
      f.write('verbose 1\n')
