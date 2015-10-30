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

"""Implementation of TR-69 objects for Glaukus Manager."""

__author__ = 'cgibson@google.com (Chris Gibson)'

import google3
import tr.cwmptypes
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181GLAUKUS = BASE.Device.X_CATAWAMPUS_ORG.Glaukus


class Glaukus(CATA181GLAUKUS):
  """Device.X_CATAWAMPUS_ORG.Glaukus."""

  @property
  def Modem(self):
    return Modem()

  @property
  def Radio(self):
    return Radio()

  @property
  def Report(self):
    return Report()


class Modem(CATA181GLAUKUS.Modem):
  """Catawampus implementation of Glaukus Manager Modem statistics."""

  ChipTemp = tr.cwmptypes.ReadOnlyFloat()
  ChipTempStatus = tr.cwmptypes.ReadOnlyString()
  ConfigHash = tr.cwmptypes.ReadOnlyString()
  FecAlarms = tr.cwmptypes.ReadOnlyInt()
  PcbCurrentDraw = tr.cwmptypes.ReadOnlyFloat()
  PcbTemp = tr.cwmptypes.ReadOnlyFloat()
  PcbTempStatus = tr.cwmptypes.ReadOnlyString()
  ResetCount = tr.cwmptypes.ReadOnlyUnsigned()
  Uptime = tr.cwmptypes.ReadOnlyUnsigned()


class Radio(CATA181GLAUKUS.Radio):
  """Catawampus implementation of Glaukus Manager Radio statistics."""

  MajorVersion = tr.cwmptypes.ReadOnlyString()
  MinorVersion = tr.cwmptypes.ReadOnlyString()


class Report(CATA181GLAUKUS.Report):
  """Catawampus implementation of Glaukus Manager Report statistics."""

  AbsMseDb = tr.cwmptypes.ReadOnlyInt()
  AdcCount = tr.cwmptypes.ReadOnlyInt()
  ExternalAgcIdx = tr.cwmptypes.ReadOnlyInt()
  InPowerRssiDbc = tr.cwmptypes.ReadOnlyInt()
  InbandPowerRssiDbc = tr.cwmptypes.ReadOnlyInt()
  InternalAgcIdx = tr.cwmptypes.ReadOnlyInt()
  MeasuredPowerRssiDbm = tr.cwmptypes.ReadOnlyInt()
  NormMseDb = tr.cwmptypes.ReadOnlyInt()
  RadMseDb = tr.cwmptypes.ReadOnlyInt()
  RxLockLossEvents = tr.cwmptypes.ReadOnlyUnsigned()
  RxLockLossTimeMs = tr.cwmptypes.ReadOnlyUnsigned()
  RxLockStatus = tr.cwmptypes.ReadOnlyBool()
  StartSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned()
  StopSampleCaptureTimeMs = tr.cwmptypes.ReadOnlyUnsigned()


if __name__ == '__main__':
  print tr.handle.DumpSchema(Glaukus())
