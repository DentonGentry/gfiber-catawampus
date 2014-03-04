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
# pylint: disable-msg=C0103

"""Implement handling for the X_GOOGLE_COM_HAT vendor data model."""

__author__ = 'irinams@google.com (Irina Stanescu)'

import google3
import tr.helpers
import tr.mainloop
import tr.types
import tr.x_gfibertv_1_0
BASETV = tr.x_gfibertv_1_0.X_GOOGLE_COM_HAT_v1_0.X_GOOGLE_COM_HAT

SYSTEMPROPS = ['/rw/sagesrv/sagesrv.properties']
USERPROPS = ['/rw/sagesrv/sagesrv_user.properties']

class TargetAttr(tr.types.Attr):
  """An attribute that has the string representation of targeting.

  You can set it to the strings 'targeting=1' or 'targeting=0'.
  """
  def validate(self, obj, value):
    if value is None:
      return value
    s = str(value).lower()
    if s == 'targeting=0':
      return False
    if s == 'targeting=1':
      return True
    return None

class Hat(BASETV):
  """Implementation of x-hat.xml."""
  HAT = tr.types.TriggerBool()
  DVRReplacement = tr.types.TriggerBool()
  Insert = tr.types.TriggerBool()
  TestCueTones = tr.types.TriggerBool()
  AFillPercent = tr.types.TriggerUnsigned()
  HTFillPercent = tr.types.TriggerUnsigned()
  SwapoutSecs = tr.types.TriggerUnsigned()
  GFTSPollingIntervalSecs = tr.types.TriggerUnsigned()
  CMSGCIntervalSecs = tr.types.TriggerUnsigned()
  FreqCapSecs = tr.types.TriggerUnsigned()

  GFTSUrl = tr.types.TriggerString()
  GFASUrl = tr.types.TriggerString()

  Target = tr.types.ReadOnly(tr.types.FileBacked(USERPROPS, TargetAttr()))

  def __init__(self):
    super(Hat, self).__init__()

  def printIfSetBool(self, f, var, name):
    if var is not None:
      if var:
        f.write('%s=1\n' % name)
      else:
        f.write('%s=0\n' % name)

  def printIfSetUnsigned(self, f, var, name):
    if var is not None:
      f.write('%s=%d\n' % (name, var))

  def printIfSetString(self, f, var, name):
    if var is not None:
      f.write('%s=%s\n' % (name, var))

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    with tr.helpers.AtomicFile(SYSTEMPROPS[0]) as f:
      self.printIfSetBool(f, self.HAT, 'hat')
      self.printIfSetBool(f, self.DVRReplacement, 'dvr_replacement')
      self.printIfSetBool(f, self.Insert, 'hat_insertion')
      self.printIfSetBool(f, self.TestCueTones, 'test_cue_tones')
      self.printIfSetUnsigned(f, self.FreqCapSecs, 'freq_cap_secs')
      self.printIfSetUnsigned(f, self.CMSGCIntervalSecs, 'cms_gc_interval_secs')
      self.printIfSetUnsigned(f, self.AFillPercent, 'a_fill_percent')
      self.printIfSetUnsigned(f, self.HTFillPercent, 'ht_fill_percent')
      self.printIfSetUnsigned(f, self.SwapoutSecs, 'hat_swapout_secs')
      self.printIfSetUnsigned(f, self.GFTSPollingIntervalSecs,
                              'gfts_polling_interval_secs')
      self.printIfSetString(f, self.GFTSUrl, 'gfts_url')
      self.printIfSetString(f, self.GFASUrl, 'gfas_url')

if __name__ == '__main__':
  print tr.core.DumpSchema(Hat())
