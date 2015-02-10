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
import tr.x_catawampus_tr181_2_0


CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device
CATA181WIFIBLASTER = CATA181DEVICE.X_CATAWAMPUS_ORG.Wifiblaster

# Unit tests can override these.
BASEDIR = ['/tmp/waveguide']
DURATION_FILE = [os.path.join(BASEDIR[0], 'wifiblaster.duration')]
ENABLE_FILE = [os.path.join(BASEDIR[0], 'wifiblaster.enable')]
INTERVAL_FILE = [os.path.join(BASEDIR[0], 'wifiblaster.interval')]
SIZE_FILE = [os.path.join(BASEDIR[0], 'wifiblaster.size')]


class Wifiblaster(CATA181WIFIBLASTER):
  """Device.X_CATAWAMPUS-ORG.Wifiblaster."""
  Duration = tr.cwmptypes.FileBacked(DURATION_FILE, tr.cwmptypes.Float())
  Enable = tr.cwmptypes.FileBacked(ENABLE_FILE, tr.cwmptypes.Bool())
  Interval = tr.cwmptypes.FileBacked(INTERVAL_FILE, tr.cwmptypes.Float())
  Size = tr.cwmptypes.FileBacked(SIZE_FILE, tr.cwmptypes.Unsigned())

  def __init__(self):
    super(Wifiblaster, self).__init__()
    try:
      os.makedirs(BASEDIR[0], 0755)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise
    self.Duration = .1
    self.Enable = False
    self.Interval = 3600
    self.Size = 64
