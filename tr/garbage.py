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
"""Helpers for checking garbage collection in tests."""

import gc


class GcChecker(object):
  """A helper class for checking whether any garbage was created.

  Example usage:
     g = GcChecker()
     ...do stuff...
     g.Check()
     ...do more stuff...
     g.Check()
     ...finish up...
     g.Done()

  This is most useful in unit tests.
  """

  def __init__(self):
    self.done = False
    self.was_enabled = gc.isenabled()
    self.was_debug = gc.get_debug()
    self.was_threshold = gc.get_threshold()
    gc.set_debug(self.was_debug | gc.DEBUG_LEAK)
    gc.enable()
    gc.set_threshold(1)
    gc.collect()
    print 'gc: GcChecker1: %d collected objects' % len(gc.garbage)
    self._CleanGc()

  def __del__(self):
    if not self.done:
      print 'WARNING: GcChecker.Done() was not called!'

  def _CleanGc(self):
    old = gc.get_debug()
    gc.set_debug(0)
    del gc.garbage[:]
    gc.collect()
    gc.set_debug(old)
    gc.collect()
    assert not gc.garbage

  def Check(self):
    """Log any garbage that was created and, if any, raise an assertion."""
    print 'gc: GcChecker2: collecting...'
    gc.collect()
    print 'gc: GcChecker2: %d collected objects' % len(gc.garbage)
    if gc.garbage:
      for i in list(gc.garbage):
        print 'gc: garbage: %r' % (i,)
      self._CleanGc()
      assert not 'garbage was found'

  def Done(self):
    """Check() and then restore the gc state to how it was before."""
    try:
      self.Check()
    finally:
      self.done = True
      gc.set_debug(self.was_debug)
      gc.set_threshold(*self.was_threshold)
      if self.was_enabled:
        gc.enable()
      else:
        gc.disable()


class GcIgnorer(object):
  """A context manager for ignoring any garbage collected for a short time."""

  def __enter__(self):
    # Collect any already-accumulated garbage; we only want to ignore
    # *new* garbage after this point.
    gc.collect()
    self.old_gc = list(gc.garbage)
    self.old_debug = gc.get_debug()
    # Disable gc debugging and clean out the garbage bin, so we don't
    # log any more garbage collections until later.
    gc.set_debug(0)
    del gc.garbage[:]

  def __exit__(self, unused_type, unused_value, unused_traceback):
    # Collect any garbage we're supposed to ignore.
    gc.collect()
    # Restore the old gc state, including the accumulated garbage.
    gc.garbage[:] = self.old_gc
    gc.set_debug(self.old_debug)
