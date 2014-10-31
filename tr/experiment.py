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
#
"""Support for 'experiments' which can be used for A/B testing."""

import google3
import cwmptypes
import x_catawampus_tr181_2_0

BASE = x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATABASE = BASE.Device.X_CATAWAMPUS_ORG


# TODO(apenwarr): All the experiment functionality.
#  This is just the basic, empty datamodel that implements the API, but
#  doesn't ever run any experiments.  We can backport this to older versions
#  so that they will accept experiment activation commands/queries, but
#  act as if there are no registered experiments (which there aren't).
class Experiments(CATABASE.Experiments):
  """Implementation of X_CATAWAMPUS-ORG_CATAWAMPUS.Experiments object."""

  Available = cwmptypes.ReadOnlyString('')
  Active = cwmptypes.ReadOnlyString('')
  Requested = cwmptypes.String('')

  def __init__(self, roothandle):
    super(Experiments, self).__init__()
    self.roothandle = roothandle
