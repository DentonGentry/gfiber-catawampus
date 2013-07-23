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
# pylint: disable-msg=W0404
#

"""Implement the tr181 Optical data model."""

__author__ = 'jnewlin@google.com (John Newlin)'

import google3

import tr.tr181_v2_6

BASE181OPTICAL = tr.tr181_v2_6.Device_v2_6.Device.Optical


class Ds6923OpticalInterface(BASE181OPTICAL.Interface):
  """TR181 Optical implementation for DS6923 optical module."""

  Enable = tr.types.ReadOnlyBool(True)
  Upstream = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')

  def __init__(self):
    super(Ds6923OpticalInterface, self).__init__()
    self.Unexport('Alias')
    self.Unexport('LastChange')
    self.Unexport('Name')
    self.Unexport('Status')
    self.Unexport(objects='Stats')

  @property
  def OpticalSignalLevel(self):
    return 0

  @property
  def LowerOpticalThreshold(self):
    return 0

  @property
  def UpperOpticalThreshold(self):
    return 0

  @property
  def TransmitOpticalLevel(self):
    return 0

  @property
  def LowerTransmitPowerThreshold(self):
    return 0

  @property
  def UpperTransmitPowerThreshold(self):
    return 0


class Ds6923Optical(BASE181OPTICAL):
  """Implementation of DS6923 Optical Module."""

  def __init__(self):
    super(Ds6923Optical, self).__init__()
    self.InterfaceList = {'1': Ds6923OpticalInterface()}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


def main():
  pass

if __name__ == '__main__':
  main()
