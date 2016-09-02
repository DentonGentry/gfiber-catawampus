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
# pylint:disable=unused-argument
#
"""Tests for experiment.py."""

import os.path
import shutil
import tempfile
import google3
import core
import experiment
from wvtest import unittest


@experiment.Experiment
def TestExp1(h):
  return [('TestParam', 1)]


@experiment.Experiment
def TestExp2(h):
  yield ('SubObj.TestParam', h.obj.TestParam)


@experiment.Experiment
def TestExpOverlap(h):
  return [('TestParam', 2),
          ('SubObj.SubObj.TestParam', 'Hello')]


class TestObject(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['TestParam'],
                objects=['SubObj'])
    self.TestParam = 5
    self.SubObj = None


class TerminalObject(core.Exporter):

  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['TestParam'])
    self.TestParam = 5


class ExperimentTest(unittest.TestCase):

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    self.old_REGDIR = experiment.REGDIR
    self.old_ACTIVEDIR = experiment.ACTIVEDIR
    experiment.REGDIR = os.path.join(self.tmpdir, 'reg')
    experiment.ACTIVEDIR = os.path.join(self.tmpdir, 'act')
    os.mkdir(experiment.REGDIR)
    os.mkdir(experiment.ACTIVEDIR)

  def tearDown(self):
    experiment.REGDIR = self.old_REGDIR
    experiment.ACTIVEDIR = self.old_ACTIVEDIR
    shutil.rmtree(self.tmpdir)

  def testExperiments(self):
    root = TestObject()
    root.SubObj = TestObject()
    root.SubObj.SubObj = TerminalObject()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    self.assertEqual(exps.Active, '')
    self.assertTrue('TestExp1' in exps.Available.split(','))
    self.assertTrue('TestExp2' in exps.Available.split(','))
    self.assertTrue('TestExpOverlap' in exps.Available.split(','))

    def Vals():
      return (root.TestParam,
              root.SubObj.TestParam,
              root.SubObj.SubObj.TestParam)

    self.assertEqual(Vals(), (5, 5, 5))
    exps.Requested = 'a, TestExp1, b'
    self.assertEqual(exps.Active, 'TestExp1')
    self.assertEqual(Vals(), (1, 5, 5))
    exps.Requested = 'TestExp1, TestExp2'
    self.assertEqual(exps.Active, 'TestExp1,TestExp2')
    self.assertEqual(Vals(), (1, 1, 5))

    # Direct writes to data model should succeed.
    # TestExp2 uses the value of root.TestParam at setup time, but
    # doesn't look at the value afterward, so changing it doesn't affect
    # root.SubObj.TestParam.
    root.TestParam = 2
    self.assertEqual(Vals(), (2, 1, 5))

    # Setting via the ExperimentHandle doesn't change the current
    # object value, but does save it for later, when the experiment is
    # unapplied.
    eh.SetExportParam('TestParam', 3)
    self.assertEqual(Vals(), (2, 1, 5))

    # Changing the set of experiments reapplies them from scratch after
    # unapplying them. That means TestExp2 recalculates its value for
    # root.SubObj.TestParam, *after* root.TestParam is restored to the
    # value it saved while TestExp1 was active.
    exps.Requested = 'TestExp2'
    self.assertEqual(Vals(), (3, 3, 5))

    # Back to defaults.
    exps.Requested = ''
    root.TestParam = 5
    self.assertEqual(Vals(), (5, 5, 5))

    # Order is significant.
    exps.Requested = 'TestExp1,TestExp2,TestExpOverlap'
    self.assertEqual(Vals(), (2, 1, 'Hello'))
    exps.Requested = 'TestExpOverlap,TestExp2,TestExp1'
    self.assertEqual(Vals(), (1, 2, 'Hello'))

    # You can apply the same experiment more than once.
    exps.Requested = 'TestExp1,TestExp2,TestExpOverlap,TestExp1'
    self.assertEqual(Vals(), (1, 1, 'Hello'))

  def testSysExperiments(self):
    # Requested system experiments at startup time are used to pre-populate
    # the Requested field.
    open(os.path.join(experiment.ACTIVEDIR, 'Splat1.requested'), 'w')
    open(os.path.join(experiment.REGDIR, 'Splat2.available'), 'w')
    open(os.path.join(experiment.ACTIVEDIR, 'Splat3.active'), 'w')
    # ...but if a requested system experiment overlaps with a cwmpd
    # experiment, it won't count, because cwmpd experiments don't persist
    # across restarts.
    open(os.path.join(experiment.ACTIVEDIR, 'TestExp2.requested'), 'w')

    root = core.Exporter()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    self.assertEqual(exps.Requested, 'Splat1,Splat3')
    self.assertEqual(exps.Available,
                     'Splat2,TestExp1,TestExp2,TestExpOverlap')
    open(os.path.join(experiment.REGDIR, 'Foo.available'), 'w')
    self.assertEqual(exps.Requested, 'Splat1,Splat3')
    self.assertEqual(exps.Available,
                     'Foo,Splat2,TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, '')  # Splat3 is active, but not available
    open(os.path.join(experiment.ACTIVEDIR, 'Foo.requested'), 'w')
    self.assertEqual(exps.Available,
                     'Foo,Splat2,TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, '')
    open(os.path.join(experiment.ACTIVEDIR, 'Foo.active'), 'w')
    self.assertEqual(exps.Available,
                     'Foo,Splat2,TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, 'Foo')
    os.unlink(os.path.join(experiment.REGDIR, 'Foo.available'))
    self.assertEqual(exps.Available,
                     'Splat2,TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, '')
    os.unlink(os.path.join(experiment.ACTIVEDIR, 'Foo.requested'))
    os.unlink(os.path.join(experiment.ACTIVEDIR, 'Foo.active'))

    open(os.path.join(experiment.REGDIR, 'Goo.available'), 'w')
    self.assertEqual(exps.Available,
                     'Goo,Splat2,TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, '')
    exps.Requested = 'Foo, Goo '
    self.assertEqual(exps.Active, '')
    self.assertTrue(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, 'Foo.requested')))
    os.rename(os.path.join(experiment.ACTIVEDIR, 'Goo.requested'),
              os.path.join(experiment.ACTIVEDIR, 'Goo.active'))
    self.assertEqual(exps.Requested, 'Foo,Goo')
    self.assertEqual(exps.Active, 'Goo')

    exps.Requested = 'Foo'
    self.assertEqual(exps.Active, 'Goo')
    os.unlink(os.path.join(experiment.ACTIVEDIR, 'Goo.active'))
    self.assertEqual(exps.Requested, 'Foo')
    self.assertEqual(exps.Active, '')
    os.unlink(os.path.join(experiment.ACTIVEDIR, 'Goo.unrequested'))
    self.assertEqual(exps.Requested, 'Foo')
    self.assertEqual(exps.Active, '')

  def testSysExperimentsInvalidCharacters(self):
    root = core.Exporter()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    exps.Requested = 'Foo/temp.test, Goo_-89'
    self.assertFalse(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, 'Foo/temp.test.requested')))
    self.assertTrue(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, 'Goo_-89.requested')))

  def testSysExperimentsLongName(self):
    root = core.Exporter()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    long_experiment = 'x' * 128
    too_long_experiment = 'y' * 129
    exps.Requested = '%s, %s' % (long_experiment, too_long_experiment)
    self.assertTrue(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, long_experiment + '.requested')))
    self.assertFalse(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, too_long_experiment + '.requested')))

  def testSysExperimentsMaxFiles(self):
    root = core.Exporter()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    for _ in range(256):
      temp = tempfile.NamedTemporaryFile(dir=experiment.ACTIVEDIR, delete=False)
      temp.close()
    exps.Requested = 'Frue'
    self.assertFalse(os.path.exists(
        os.path.join(experiment.ACTIVEDIR, 'Frue.requested')))

  def testSysExperimentsExistAtStartup(self):
    open(os.path.join(experiment.ACTIVEDIR, 'Foo.active'), 'w')
    open(os.path.join(experiment.ACTIVEDIR, 'Goo.requested'), 'w')
    open(os.path.join(experiment.ACTIVEDIR, 'Grue.active'), 'w')
    open(os.path.join(experiment.ACTIVEDIR, 'Grue.unrequested'), 'w')

    root = core.Exporter()
    eh = experiment.ExperimentHandle(root)
    exps = experiment.Experiments(eh)
    eh.root_experiments = exps

    self.assertEqual(exps.Requested, 'Foo,Goo')
    self.assertEqual(exps.Available, 'TestExp1,TestExp2,TestExpOverlap')
    self.assertEqual(exps.Active, '')
    open(os.path.join(experiment.REGDIR, 'Foo.available'), 'w')
    self.assertEqual(exps.Active, 'Foo')
    open(os.path.join(experiment.REGDIR, 'Goo.available'), 'w')
    self.assertEqual(exps.Active, 'Foo')
    open(os.path.join(experiment.REGDIR, 'Grue.available'), 'w')
    self.assertEqual(exps.Active, 'Foo,Grue')
    self.assertEqual(exps.Requested, 'Foo,Goo')


if __name__ == '__main__':
  unittest.main()
