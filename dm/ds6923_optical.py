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

import math

import google3
import i2c

import tr.tr181_v2_6
import tr.types

BASE181OPTICAL = tr.tr181_v2_6.Device_v2_6.Device.Optical
I2C_BUS = None

TX_POWER_HIGH_ALARM = 24
TX_POWER_LOW_ALARM = 26
RX_POWER_HIGH_ALARM = 32
RX_POWER_LOW_ALARM = 34
TX_OPTICAL_OUTPUT_POWER = 102
RX_OPTICAL_INPUT_POWER = 104

class Ds6923OpticalInterface(BASE181OPTICAL.Interface):
  """TR181 Optical implementation for DS6923 optical module."""

  Enable = tr.types.ReadOnlyBool(True)
  Upstream = tr.types.ReadOnlyBool(True)
  LowerLayers = tr.types.ReadOnlyString('')

  def __init__(self, i2c_addr):
    super(Ds6923OpticalInterface, self).__init__()
    self.Unexport(['Alias', 'LastChange', 'Name', 'Status'])
    self.Unexport(objects=['Stats'])
    # The i2c module shifts the address right by 1 for some reason.
    self.i2c_addr = i2c_addr << 1
    self.i2c = i2c.Util(I2C_BUS)

  def ReadWord(self, offset):
    vals = self.i2c.Read(self.i2c_addr, offset, 2)
    if not vals or len(vals) != 2:
      raise ValueError('i2c read did not return 2 bytes of data.')
    return (int(vals[0]) << 8) | int(vals[1])

  def MilliWattToDbm(self, val):
    return 10 * math.log(val, 10)

  def GetDbmValue(self, offset):
    """Read from an i2c offset and convert to tr181 dbm format."""
    val = self.ReadWord(offset)
    val = float(val) / 10000.0  # Get the value in milli-watts.
    # From spec:
    # The value is measured in dBm/1000, i.e. the value divided by 1000 is dB
    # relative to 1 mW. For example, -12345 means -12.345 dBm, 0 means 0 dBm (1
    # mW) and 12345 means 12.345 dBm.
    return int(1000 * self.MilliWattToDbm(val))

  @property
  def OpticalSignalLevel(self):
    return self.GetDbmValue(RX_OPTICAL_INPUT_POWER)

  @property
  def LowerOpticalThreshold(self):
    return self.GetDbmValue(RX_POWER_LOW_ALARM)

  @property
  def UpperOpticalThreshold(self):
    return self.GetDbmValue(RX_POWER_HIGH_ALARM)

  @property
  def TransmitOpticalLevel(self):
    return self.GetDbmValue(TX_OPTICAL_OUTPUT_POWER)

  @property
  def LowerTransmitPowerThreshold(self):
    return self.GetDbmValue(TX_POWER_LOW_ALARM)

  @property
  def UpperTransmitPowerThreshold(self):
    return self.GetDbmValue(TX_POWER_HIGH_ALARM)


class Ds6923Optical(BASE181OPTICAL):
  """Implementation of DS6923 Optical Module."""

  def __init__(self, i2c_addr):
    super(Ds6923Optical, self).__init__()
    self.InterfaceList = {'1': Ds6923OpticalInterface(i2c_addr)}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)
