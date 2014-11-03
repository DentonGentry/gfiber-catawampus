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

# unittest requires method names starting in 'test'
# pylint:disable=invalid-name

"""Unit tests for ds6923_optical.py implementation."""

__author__ = 'jnewlin@google.com (John Newlin)'

import google3
from tr.wvtest import unittest
import mox
import ds6923_optical


class FakeI2cBus(object):
  """Emulator is a fake I2c Helper."""

  def Read(self, unused_addr, unused_offset, unused_length):
    """Read data from i2c address."""
    return []

  def Write(self, unused_addr, unused_offset, unused_buf):
    """Write data to i2c address."""
    pass


class Ds6923OpticalTest(unittest.TestCase):
  def setUp(self):
    self.save_bus = ds6923_optical.I2C_BUS
    self.fake_bus = FakeI2cBus()
    ds6923_optical.I2C_BUS = self.fake_bus
    self.ds6923 = ds6923_optical.Ds6923OpticalInterface(0x51)

  def tearDown(self):
    ds6923_optical.I2C_BUS = self.save_bus

  def testMilliWattToDb(self):
    self.assertAlmostEqual(0, self.ds6923.MilliWattToDbm(1))
    self.assertAlmostEqual(-10, self.ds6923.MilliWattToDbm(0.1))
    self.assertAlmostEqual(40, self.ds6923.MilliWattToDbm(10000))

  def testReadWord(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 100, 2).AndReturn([1, 2])
    self.ds6923.i2c.Read(mox.IsA(int), 100, 2).AndReturn([0xff, 0xff])
    m.ReplayAll()
    self.assertEqual(1<<8 | 2, self.ds6923.ReadWord(100))
    self.assertEqual(0xffff, self.ds6923.ReadWord(100))
    m.UnsetStubs()
    m.VerifyAll()

  def testOpticalSignalLevel(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 104, 2).AndReturn([2, 128])
    m.ReplayAll()
    self.assertEqual(-11938, self.ds6923.OpticalSignalLevel)
    m.UnsetStubs()
    m.VerifyAll()

  def testLowerOpticalThreshold(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 34, 2).AndReturn([200, 20])
    m.ReplayAll()
    self.assertEqual(7094, self.ds6923.LowerOpticalThreshold)
    m.UnsetStubs()
    m.VerifyAll()


  def testUpperOpticalThreshold(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 32, 2).AndReturn([20, 200])
    m.ReplayAll()
    self.assertEqual(-2740, self.ds6923.UpperOpticalThreshold)
    m.UnsetStubs()
    m.VerifyAll()

  def testTransmitOpticalLevel(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 102, 2).AndReturn([10, 120])
    m.ReplayAll()
    self.assertEqual(-5718, self.ds6923.TransmitOpticalLevel)
    m.UnsetStubs()
    m.VerifyAll()

  def testLowerTransmitPowerThreshold(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 26, 2).AndReturn([4, 126])
    m.ReplayAll()
    self.assertEqual(-9393, self.ds6923.LowerTransmitPowerThreshold)
    m.UnsetStubs()
    m.VerifyAll()

  def testUpperTransmitPowerThreshold(self):
    m = mox.Mox()
    m.StubOutWithMock(self.ds6923.i2c, 'Read')
    self.ds6923.i2c.Read(mox.IsA(int), 24, 2).AndReturn([3, 127])
    m.ReplayAll()
    self.assertEqual(-10481, self.ds6923.UpperTransmitPowerThreshold)
    m.UnsetStubs()
    m.VerifyAll()


if __name__ == '__main__':
  unittest.main()
