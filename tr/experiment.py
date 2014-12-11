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
# pylint:disable=invalid-name
#
"""Support for 'experiments' which can be used for A/B testing."""

import errno
import os
import traceback
import google3
import cwmptypes
import handle
import helpers
import x_catawampus_tr181_2_0

REGDIR = helpers.Path('/tmp/experiments')
ACTIVEDIR = helpers.Path('/config/experiments')

BASE = x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATABASE = BASE.Device.X_CATAWAMPUS_ORG


# The global list of all experiments registered with @Experiment
registered = {}


def _ListIfExists(dirname):
  try:
    return os.listdir(dirname)
  except OSError as e:
    if e.errno == errno.ENOENT:
      return []
    raise


def _GetSystemExperiments(dirname, suffix):
  out = set()
  for name in _ListIfExists(dirname):
    if name.endswith(suffix):
      out.add(name[:-len(suffix)])
  return out


def Experiment(fn):
  """Wrapper function for registering new experiments.

  For example, to register an experiment called MyExperiment:
      @Experiment
      def MyExperiment(roothandle):
        return [('My.Test.Param', 7),
                ('My.Test.Param2', roothandle.obj.Dynamic.Test.Value),
                ('My.Test.Param3', random.random())]

  Args:
    fn: the function to wrap.
  Returns:
    fn, after registering fn with the experiment framework.
  """
  name = fn.__name__
  print 'Registering experiment %r' % name
  registered[fn.__name__] = fn
  return fn


class Experiments(CATABASE.Experiments):
  """Implementation of X_CATAWAMPUS-ORG_CATAWAMPUS.Experiments object.

  This object is part of the TR-069 data model and allows you to activate
  and deactivate experiments by setting the 'Requested' member.
  """

  def __init__(self, roothandle):
    super(Experiments, self).__init__()
    self.force_values = {}
    self.saved_values = {}
    self.roothandle = roothandle
    assert hasattr(roothandle, 'inner')
    self.active = []
    # Read initial value of requested system experiments from the filesystem
    try:
      # This will trigger Triggered(), but can't be allowed to throw an
      # exception at startup time, so catch it if something goes wrong.
      req = ((_GetSystemExperiments(ACTIVEDIR, '.active') |
              _GetSystemExperiments(ACTIVEDIR, '.requested')) -
             _GetSystemExperiments(ACTIVEDIR, '.unrequested'))
      self.Requested = ','.join(sorted(req))
    except (IOError, OSError) as e:
      traceback.print_exc()
      print "Experiments: can't init self.Requested: %r" % e

  @property
  def Available(self):
    avail = set(registered.keys())
    sysavail = _GetSystemExperiments(REGDIR, '.available')
    return ','.join(sorted(avail | sysavail))

  # TODO(apenwarr): make experiments persist across reboots.
  #  Without such a feature, we won't be able to make experiments that
  #  affect the early boot process (such as driver loading).
  Requested = cwmptypes.TriggerString('')

  @Requested.validator
  def Requested(self, v):
    # Note: unlike Available, order of the Requested object is significant,
    # so we shouldn't sort it.
    return ','.join(i.strip() for i in v.split(','))

  @property
  def Active(self):
    # Note: unlike Available, order of the Active object is significant,
    # so we shouldn't sort it.
    available = self.Available
    active = [name for name, unused_obj in self.active]
    sysactive = set()
    for name in _ListIfExists(ACTIVEDIR):
      if name.endswith('.active'):
        exp = name[:-7]
        if exp in available:
          sysactive.add(exp)
    return ','.join(active + sorted(sysactive))

  def Triggered(self):
    """Triggered whenever Requested is changed."""

    # Flush old experiments
    keys = self.saved_values.keys()
    lookups = self.roothandle.inner.LookupExports(keys)
    for k, (h, param) in zip(keys, lookups):
      h.SetExportParam(param, self.saved_values[k])
    del self.active[:]
    self.force_values.clear()
    self.saved_values.clear()

    # TODO(apenwarr): use transactions like api.SetParameterValues() does.
    print 'Experiments requested: %r' % self.Requested
    sysavail = _GetSystemExperiments(REGDIR, '.available')
    sysactive = _GetSystemExperiments(ACTIVEDIR, '.active')
    sysrequested = _GetSystemExperiments(ACTIVEDIR, '.requested')

    reqstr = self.Requested
    requested = reqstr.split(',') if reqstr else []
    for name in requested:
      if name in sysavail:
        print 'Requesting system experiment %r' % name
        helpers.Unlink(os.path.join(ACTIVEDIR, name + '.unrequested'))
        if not os.path.exists(os.path.join(ACTIVEDIR, name + '.active')):
          helpers.WriteFileAtomic(
              os.path.join(ACTIVEDIR, name + '.requested'), '')
      expfunc = registered.get(name)
      if not expfunc:
        if name not in sysavail:
          print 'no such experiment: %r' % name
      else:
        print 'Applying experiment %r' % name
        forces = list(expfunc(self.roothandle))
        self.force_values.update(forces)
        keys = [f[0] for f in forces]
        lookups = list(self.roothandle.inner.LookupExports(keys))
        for (k, _), (h, param) in zip(forces, lookups):
          if k not in self.saved_values:
            print '  Saving pre-experiment value for %r' % k
            self.saved_values[k] = h.GetExport(param)
        for (k, v), (h, param) in zip(forces, lookups):
          print '  Writing new value for %r = %r' % (k, v)
          h.SetExportParam(param, v)
        self.active.append((name, forces))

    for name in sysactive | sysrequested:
      if name not in requested:
        print 'Unrequesting system experiment %r' % name
        helpers.Unlink(os.path.join(ACTIVEDIR, name + '.requested'))
        if os.path.exists(os.path.join(ACTIVEDIR, name + '.active')):
          helpers.WriteFileAtomic(
              os.path.join(ACTIVEDIR, name + '.unrequested'), '')

    print 'Experiments now active: %r' % self.Active


class ExperimentHandle(handle.Handle):
  """A variant of handle.Handle that prevents overwriting experiment values.

  If an experiment is active and you use SetExportParam() to write to one of
  the affected variables, the write will be captured and saved for later
  (ie. if the experiment is stopped), at which time the value will be written
  to the data model.  In the meantime, the experimental setting is the one
  that is used.

  Writing directly to the data model (ie. bypassing the handle altogether)
  still goes through.  That's important so that objects can still update
  their status and internal settings, etc.
  """

  def __init__(self, obj, basename='', roothandle=None):
    super(ExperimentHandle, self).__init__(obj, basename=basename,
                                           roothandle=roothandle)
    self.root_experiments = None

  @property
  def inner(self):
    if self.roothandle:
      return self.roothandle.inner.Sub(self.basename)
    elif self.basename:
      return handle.Handle(self.obj).Sub(self.basename)
    else:
      return handle.Handle(self.obj)

  @property
  def experiments(self):
    if self.roothandle:
      return self.roothandle.experiments
    else:
      return self.root_experiments

  def SetExportParam(self, name, value):
    if self.basename:
      fullname = self.basename + '.' + name
    else:
      fullname = name
    ex = self.experiments
    if fullname in ex.saved_values:
      ex.saved_values[fullname] = value
      return self.inner.FindExport(name)[0].obj
    else:
      return self.inner.SetExportParam(name, value)
