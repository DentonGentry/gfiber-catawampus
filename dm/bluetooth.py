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
#
"""An implementation of Device.X_CATAWAMPUS-ORG.Bluetooth."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import json
import subprocess
import google3
import tr.cwmptypes
import tr.mainloop
import tr.x_catawampus_tr181_2_0


IBEACONCMD = ['ibeacon']
EDDYSTONECMD = ['eddystone']
INVENTORY_GLOB = ['/user/bluez/lib/bluetooth/*/*/gfiber-inventory']
CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device


class Bluetooth(CATA181DEVICE.X_CATAWAMPUS_ORG.Bluetooth):
  """Implementation of X_CATAWAMPUS-ORG.Bluetooth."""

  RemoteControlNumberOfEntries = tr.cwmptypes.NumberOf('RemoteControlList')

  def __init__(self):
    super(Bluetooth, self).__init__()
    self.iBeacon = iBeacon()
    self.Eddystone = Eddystone()

  @property
  def RemoteControlList(self):
    """Return a list of RemoteControl objects, from Blue/Z gfiber-inventory."""
    rcfiles = glob.glob(INVENTORY_GLOB[0])
    rcnum = 1
    rclist = {}
    for rc in sorted(rcfiles):
      jsondata = {}
      try:
        jsondata = json.load(open(rc))
      except (OSError, IOError, ValueError):
        print 'Bad Remote Control JSON file %s' % rc
        continue
      if 'bdaddr' in jsondata and 'model' in jsondata:
        rclist[rcnum] = RemoteControl(jsondata)
        rcnum += 1
    return rclist


class iBeacon(CATA181DEVICE.X_CATAWAMPUS_ORG.Bluetooth.iBeacon):
  """Implementation of X_CATAWAMPUS-ORG.Bluetooth.iBeacon."""
  Enable = tr.cwmptypes.TriggerBool(False)
  UUID = tr.cwmptypes.TriggerString('')
  Major = tr.cwmptypes.TriggerUnsigned(0)
  Minor = tr.cwmptypes.TriggerUnsigned(0)
  TxPower = tr.cwmptypes.TriggerUnsigned(0)

  @tr.mainloop.WaitUntilIdle
  def StartStop(self):
    if self.Major and self.Minor and self.UUID and self.TxPower and self.Enable:
      args = IBEACONCMD + ['-u', self.UUID, '-m', str(self.Major),
                           '-n', str(self.Minor), '-t', str(self.TxPower)]
      rc = subprocess.call(args)
      if rc != 0:
        print 'iBeacon config failed rc=%d' % rc
    else:
      rc = subprocess.call(IBEACONCMD + ['-d'])
      if rc != 0:
        print 'iBeacon disable failed rc=%d' % rc

  def Triggered(self):
    self.StartStop()


class Eddystone(CATA181DEVICE.X_CATAWAMPUS_ORG.Bluetooth.Eddystone):
  """Implementation of X_CATAWAMPUS-ORG.Bluetooth.Eddystone."""
  Enable = tr.cwmptypes.TriggerBool(False)
  Namespace = tr.cwmptypes.TriggerString('')
  Instance = tr.cwmptypes.TriggerString('')
  TxPower = tr.cwmptypes.TriggerInt(0)

  @tr.mainloop.WaitUntilIdle
  def StartStop(self):
    if self.Namespace and self.Instance and self.Enable:
      args = EDDYSTONECMD + ['-n', self.Namespace, '-i', self.Instance,
                             '-t', str(self.TxPower)]
      rc = subprocess.call(args)
      if rc != 0:
        print 'Eddystone config failed rc=%d' % rc
    else:
      rc = subprocess.call(EDDYSTONECMD + ['-d'])
      if rc != 0:
        print 'Eddystone disable failed rc=%d' % rc

  def Triggered(self):
    self.StartStop()


class RemoteControl(CATA181DEVICE.X_CATAWAMPUS_ORG.Bluetooth.RemoteControl):
  """Implementation of X_CATAWAMPUS-ORG.Bluetooth.RemoteControl."""
  FirmwareVersion = tr.cwmptypes.ReadOnlyString('')
  HardwareVersion = tr.cwmptypes.ReadOnlyString('')
  Model = tr.cwmptypes.ReadOnlyString('')
  PhysAddress = tr.cwmptypes.ReadOnlyString('')
  SerialNumber = tr.cwmptypes.ReadOnlyString('')

  def __init__(self, jsondata):
    super(RemoteControl, self).__init__()
    type(self).FirmwareVersion.Set(self, jsondata.get('firmware', ''))
    type(self).HardwareVersion.Set(self, jsondata.get('hardware', ''))
    type(self).Model.Set(self, jsondata.get('model', ''))
    type(self).PhysAddress.Set(self, jsondata.get('bdaddr', ''))
    type(self).SerialNumber.Set(self, jsondata.get('serial', ''))
