#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Implementation of tr-181 Device.DNS hierarchy of objects.

Handles the Device.DNS portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-6-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.types
import tr.x_catawampus_tr181_2_0

BASEDNS = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.DNS
DNS_CHECK_FILE = ['/tmp/dnsck_servers']


class DNS(BASEDNS):
  """tr181 Device.DNS object."""

  SupportedRecordTypes = tr.types.ReadOnlyString('A,AAAA,SRV,PTR')

  def __init__(self):
    super(DNS, self).__init__()
    self.Unexport(objects='Client')
    self.Unexport(objects='Relay')
    self.Diagnostics = Diagnostics()


class Diagnostics(BASEDNS.Diagnostics):
  """tr181 Device.DNS.Diagnostics object."""

  X_CATAWAMPUS_ORG_ExtraCheckServers = tr.types.FileBacked(
      DNS_CHECK_FILE, tr.types.String())

  def __init__(self):
    super(Diagnostics, self).__init__()
