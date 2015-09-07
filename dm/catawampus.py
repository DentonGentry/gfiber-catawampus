#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Implementation of the x-catawampus-org vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import cProfile
import json
import pstats
import StringIO
import sys
import google3
import dm.periodic_statistics
import tr.api
import tr.cwmptypes
import tr.experiment
import tr.handle
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATABASE = BASE.Device.X_CATAWAMPUS_ORG.Catawampus


class CatawampusDm(CATABASE):
  """Implementation of catawampus extension. See tr/schema/x-cata181.xml."""

  def __init__(self, roothandle):
    super(CatawampusDm, self).__init__()
    self.roothandle = roothandle
    self.Profiler = Profiler()
    self.ExpensiveStuff = ExpensiveStuff()
    self.Experiments = tr.experiment.Experiments(roothandle)
    self.Export(objects=['Experiments'])

  @property
  def RuntimeEnvInfo(self):
    """Return string of interesting settings from Python environment."""
    python = dict()
    python['exec_prefix'] = sys.exec_prefix
    python['executable'] = sys.executable
    python['path'] = str(sys.path)
    python['platform'] = sys.platform
    python['prefix'] = sys.prefix
    python['version'] = sys.version

    env = dict()
    env['python'] = python

    return json.dumps(env)


class Profiler(CATABASE.Profiler):
  """Implements a profiler for cwmpd."""

  Enable = tr.cwmptypes.TriggerBool(False)
  Result = tr.cwmptypes.ReadOnlyString('')

  def __init__(self):
    super(Profiler, self).__init__()
    self.prof = None

  def Triggered(self):
    if self.Enable and not self.prof:
      self.prof = cProfile.Profile()
      self.prof.enable()
    if not self.Enable and self.prof:
      self.prof.disable()
      s = StringIO.StringIO()
      ps = pstats.Stats(self.prof, stream=s).sort_stats('cumulative')
      ps.print_stats()
      val = s.getvalue()
      type(self).Result.Set(self, val[:16384])
      self.prof = None


class ExpensiveStuff(CATABASE.ExpensiveStuff):
  """Tracks expensive background activities."""

  def getTopNSamples(self, samples, lim):
    """Return the lim most expensive samples."""
    expensive = sorted(samples, key=samples.get, reverse=True)
    report = ''
    for param in expensive[0:lim]:
      report += '%s: %s\n' % (param, samples[param])
    return report

  def GetEnable(self):
    a = tr.api.ExpensiveNotificationsEnable
    b = dm.periodic_statistics.ExpensiveStatsEnable
    return a and b

  def SetEnable(self, value):
    b = bool(value)
    tr.api.ExpensiveNotificationsEnable = b
    dm.periodic_statistics.ExpensiveStatsEnable = b

  Enable = property(GetEnable, SetEnable, None, 'ExpensiveStuff.Enable')

  @property
  def Notifications(self):
    return self.getTopNSamples(tr.api.ExpensiveNotifications, 40)

  @property
  def Stats(self):
    return self.getTopNSamples(dm.periodic_statistics.ExpensiveStats, 40)


if __name__ == '__main__':
  sys.path.append('../')
  cm = CatawampusDm(None)
  print tr.handle.Dump(cm)
