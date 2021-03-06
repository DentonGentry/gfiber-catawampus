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
# pylint: disable=invalid-name

"""Implementation of TR-181 objects for Wifiblaster."""

__author__ = 'mikemu@google.com (Mike Mu)'

import errno
import os
import google3
import tr.cwmptypes
import tr.experiment
import tr.x_catawampus_tr181_2_0


CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device
CATA181WIFIBLASTER = CATA181DEVICE.X_CATAWAMPUS_ORG.Wifiblaster


@tr.experiment.Experiment
def EnableWifiblaster1470(_):
  return [('Device.X_CATAWAMPUS-ORG.Wifiblaster.Duration', .1),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Fraction', 10),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Interval', 3600),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Size', 1470),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Enable', True)]


@tr.experiment.Experiment
def EnableWifiblaster800(_):
  return [('Device.X_CATAWAMPUS-ORG.Wifiblaster.Duration', .1),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Fraction', 10),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Interval', 3600),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Size', 800),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Enable', True)]


@tr.experiment.Experiment
def EnableWifiblaster60(_):
  return [('Device.X_CATAWAMPUS-ORG.Wifiblaster.Duration', .1),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Fraction', 10),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Interval', 3600),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Size', 60),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Enable', True)]


@tr.experiment.Experiment
def EnableWifiblasterDebug(_):
  return [('Device.X_CATAWAMPUS-ORG.Wifiblaster.Duration', 1),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Fraction', 10),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Interval', 3600),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Size', 1470),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Enable', True)]


@tr.experiment.Experiment
def EnableWifiblasterOnAssociation(_):
  return [('Device.X_CATAWAMPUS-ORG.Wifiblaster.Duration', .1),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Fraction', 10),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.OnAssociation', True),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Size', 1470),
          ('Device.X_CATAWAMPUS-ORG.Wifiblaster.Enable', True)]


# Unit tests can override these.
BASEDIR = ['/tmp/waveguide']
DURATION_FILE = ['/tmp/waveguide/wifiblaster.duration']
ENABLE_FILE = ['/tmp/waveguide/wifiblaster.enable']
FRACTION_FILE = ['/tmp/waveguide/wifiblaster.fraction']
INTERVAL_FILE = ['/tmp/waveguide/wifiblaster.interval']
MEASUREALL_FILE = ['/tmp/waveguide/wifiblaster.measureall']
ONASSOCIATION_FILE = ['/tmp/waveguide/wifiblaster.onassociation']
SIZE_FILE = ['/tmp/waveguide/wifiblaster.size']


class Wifiblaster(CATA181WIFIBLASTER):
  """Device.X_CATAWAMPUS-ORG.Wifiblaster."""
  Duration = tr.cwmptypes.FileBacked(DURATION_FILE, tr.cwmptypes.Float())
  Enable = tr.cwmptypes.FileBacked(ENABLE_FILE, tr.cwmptypes.Bool())
  Fraction = tr.cwmptypes.FileBacked(FRACTION_FILE, tr.cwmptypes.Unsigned())
  Interval = tr.cwmptypes.FileBacked(INTERVAL_FILE, tr.cwmptypes.Float())
  MeasureAll = tr.cwmptypes.FileBacked(MEASUREALL_FILE, tr.cwmptypes.Float())
  OnAssociation = tr.cwmptypes.FileBacked(ONASSOCIATION_FILE,
                                          tr.cwmptypes.Bool())
  Size = tr.cwmptypes.FileBacked(SIZE_FILE, tr.cwmptypes.Unsigned())

  def __init__(self):
    super(Wifiblaster, self).__init__()
    try:
      os.makedirs(BASEDIR[0], 0755)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise
    self.Duration = 0
    self.Enable = False
    self.Fraction = 0
    self.Interval = 0
    self.MeasureAll = 0
    self.OnAssociation = False
    self.Size = 0
