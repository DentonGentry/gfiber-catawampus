#!/usr/bin/python
# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Implementation of TR-181 objects for Glaukus."""

__author__ = 'cgibson@google.com (Chris Gibson)'

import google3
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181GLAUKUS = BASE.Device.X_CATAWAMPUS_ORG.Glaukus


class Glaukus(CATA181GLAUKUS):
  """Device.X_CATAWAMPUS_ORG.Glaukus."""

  AbsMseDb = tr.cwmptypes.ReadOnlyInt(0)
  AdcCount = tr.cwmptypes.ReadOnlyInt(0)
  ExternalAgcIdx = tr.cwmptypes.ReadOnlyInt(0)
  InPowerRssiDbc = tr.cwmptypes.ReadOnlyInt(0)
  InbandPowerRssiDbc = tr.cwmptypes.ReadOnlyInt(0)
  InternalAgcIdx = tr.cwmptypes.ReadOnlyInt(0)
  MeasuredPowerRssiDbm = tr.cwmptypes.ReadOnlyInt(0)
  NormMseDb = tr.cwmptypes.ReadOnlyInt(0)
  RadMseDb = tr.cwmptypes.ReadOnlyInt(0)
  RxLockLossEvents = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxLockLossTimeMs = tr.cwmptypes.ReadOnlyUnsigned(0)
  RxLockStatus = tr.cwmptypes.ReadOnlyBool()
  StartSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned(0)
  StopSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned(0)


if __name__ == '__main__':
  print tr.handle.DumpSchema(Glaukus())
