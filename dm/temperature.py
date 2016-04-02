#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

"""Implementation of tr-181 Device.DeviceInfo.TemperatureStatus object.

Handles the Device.DeviceInfo.TemperatureStatus portion of TR-181, as
described by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import subprocess
import time
import tornado.ioloop
import tr.basemodel
import tr.cwmptypes

BASE181 = tr.basemodel
BASE181TEMPERATURE = BASE181.Device.DeviceInfo.TemperatureStatus
CATA181DI = BASE181.Device.DeviceInfo
NUMBER = re.compile(r'(\d+(?:\.\d+)?)')

# tr-181 defines a temperature below 0 Kelvin as "Invalid temperature"
BADCELSIUS = -274

DEFAULTPOLL = 300
UNKNOWN_TIME = tr.cwmpdate.format(0)

# Unit tests can override these with fake data
HDDTEMPERATURE = 'hdd-temperature'
PERIODICCALL = tornado.ioloop.PeriodicCallback
TIMENOW = time.gmtime


def GetNumberFromFile(filename):
  """Extract a number from a file.

  The number can be an integer or float. If float, it will be rounded.

  Args:
    filename: the file to read.
  Returns:
    an integer.
  Raises:
    ValueError: if the file did not contain a number.
  """
  with open(filename, 'r') as f:
    result = NUMBER.search(f.readline())
    if result is not None:
      return int(round(float(result.group(0))))
  raise ValueError('No number found in %s' % filename)


class TemperatureSensor(BASE181TEMPERATURE.TemperatureSensor):
  """Implements tr-181 TemperatureStatus.TemperatureSensor.

     Args:
       name: a descriptive name for this sensor.
       sensor: an object with a GetTemperature() method.

     This class implements the hardware and platform-independant portions
     of a TemperatureSensor. It periodically calls sensor.GetTemperature()
     to obtain a sample from the hardware.
  """

  Enable = tr.cwmptypes.TriggerBool(True)
  HighAlarmTime = tr.cwmptypes.ReadOnlyDate(0)
  HighAlarmValue = tr.cwmptypes.TriggerInt(BADCELSIUS)
  LastUpdate = tr.cwmptypes.ReadOnlyDate(0)
  LowAlarmTime = tr.cwmptypes.ReadOnlyDate(0)
  LowAlarmValue = tr.cwmptypes.TriggerInt(BADCELSIUS)
  MinTime = tr.cwmptypes.ReadOnlyDate(0)
  MinValue = tr.cwmptypes.ReadOnlyInt(BADCELSIUS)
  MaxTime = tr.cwmptypes.ReadOnlyDate(0)
  MaxValue = tr.cwmptypes.ReadOnlyInt(BADCELSIUS)
  Name = tr.cwmptypes.ReadOnlyString('')
  PollingInterval = tr.cwmptypes.TriggerUnsigned(DEFAULTPOLL)
  Reset = tr.cwmptypes.TriggerBool(False)
  ResetTime = tr.cwmptypes.ReadOnlyDate(0)
  Value = tr.cwmptypes.ReadOnlyInt(BADCELSIUS)

  def __init__(self, name, sensor, ioloop=None):
    super(TemperatureSensor, self).__init__()
    self.Unexport(['Alias'])
    type(self).Name.Set(self, name)
    self._sensor = sensor
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.scheduler = None
    self._ResetReadings()
    self._Configure()

  def _ResetReadings(self):
    type(self).HighAlarmTime.Set(self, 0)
    type(self).LowAlarmTime.Set(self, 0)
    type(self).LastUpdate.Set(self, 0)
    type(self).MaxTime.Set(self, 0)
    type(self).MaxValue.Set(self, BADCELSIUS)
    type(self).MinTime.Set(self, 0)
    type(self).MinValue.Set(self, BADCELSIUS)
    type(self).ResetTime.Set(self, 0)
    type(self).Value.Set(self, BADCELSIUS)

  def Triggered(self):
    if self.Reset:
      self._ResetReadings()
      self.Reset = False
      type(self).ResetTime.Set(self, TIMENOW())
    self._Configure()

  @property
  def Status(self):
    return 'Enabled' if self.Enable else 'Disabled'

  def SampleTemperature(self):
    t = self._sensor.GetTemperature()
    type(self).Value.Set(self, t)
    now = TIMENOW()
    type(self).LastUpdate.Set(self, now)
    if t < self.MinValue or self.MinValue == BADCELSIUS:
      type(self).MinValue.Set(self, t)
      type(self).MinTime.Set(self, now)
    if t > self.MaxValue:
      type(self).MaxValue.Set(self, t)
      type(self).MaxTime.Set(self, now)
    if t > self.HighAlarmValue:
      type(self).HighAlarmTime.Set(self, now)
    if t < self.LowAlarmValue:
      type(self).LowAlarmTime.Set(self, now)

  def _Configure(self):
    if self.scheduler is not None:
      self.scheduler.stop()
      self.scheduler = None
    if self.Enable:
      self.scheduler = (
          PERIODICCALL(
              self.SampleTemperature,
              self.PollingInterval * 1000,
              io_loop=self.ioloop))
      self.scheduler.start()


class SensorHdparm(object):
  """Hard drive temperature sensor implementation.

     This object can be passed as the sensor argument to a
     TemperatureSensor object, to monitor hard drive temperature.
  """

  DRIVETEMP = re.compile(r'drive temperature \(celsius\) is:\s*(\d+(?:\.\d+)?)')

  def __init__(self, dev):
    self._dev = dev if dev[0] == '/' else '/dev/' + dev

  def GetTemperature(self):
    hd = subprocess.Popen([HDDTEMPERATURE, self._dev], stdout=subprocess.PIPE)
    out, _ = hd.communicate(None)
    try:
      return int(out)
    except ValueError:
      return BADCELSIUS


class SensorReadFromFile(object):
  """Read a temperature from an arbitrary file.

     Opens a file looks for a number in the first line.
     By default this is treated as a temperature in degrees Celsius, but a
     divisor can be optionally passed to the constructor to handle smaller
     units.

     This object can be passed as the sensor argument to a
     TemperatureSensor object, to monitor an arbitrary
     temperature written to a file.
  """

  def __init__(self, filename, divisor=1):
    self._filename = filename
    if divisor <= 0:
      raise ValueError('Bad divisor: %r' % divisor)
    self._divisor = divisor

  def GetTemperature(self):
    try:
      temp = GetNumberFromFile(self._filename)
      return temp / self._divisor
    except (IOError, ValueError):
      print 'TempFromFile %s: bad value' % self._filename
      return BADCELSIUS


class TemperatureStatus(CATA181DI.TemperatureStatus):
  """Implementation of tr-181 DeviceInfo.TemperatureStatus."""

  TemperatureSensorNumberOfEntries = tr.cwmptypes.NumberOf(
      'TemperatureSensorList')
  X_CATAWAMPUS_ORG_FanNumberOfEntries = tr.cwmptypes.NumberOf(
      'X_CATAWAMPUS_ORG_FanList')

  def __init__(self):
    super(TemperatureStatus, self).__init__()
    self.TemperatureSensorList = dict()
    self._next_sensor_number = 1
    self.X_CATAWAMPUS_ORG_FanList = dict()
    self._next_fan_number = 1

  def AddSensor(self, name, sensor):
    ts = TemperatureSensor(name=name, sensor=sensor)
    ts.SampleTemperature()
    self.TemperatureSensorList[self._next_sensor_number] = ts
    self._next_sensor_number += 1

  def AddFan(self, fan):
    self.X_CATAWAMPUS_ORG_FanList[self._next_fan_number] = fan
    self._next_fan_number += 1


class FanReadFileRPS(CATA181DI.TemperatureStatus.X_CATAWAMPUS_ORG_Fan):
  """Implementation of Fan object, reading rev/sec from a file."""

  Name = tr.cwmptypes.ReadOnlyString('')

  def __init__(self, name, filename):
    super(FanReadFileRPS, self).__init__()
    type(self).Name.Set(self, name)
    self._filename = filename

  @property
  def RPM(self):
    try:
      rps = GetNumberFromFile(self._filename)
      return rps * 60
    except ValueError as e:
      print 'FanReadFileRPS bad value %s: %s' % (self._filename, e)
      return -1

  @property
  def DesiredRPM(self):
    return -1

  @property
  def DesiredPercentage(self):
    return -1
