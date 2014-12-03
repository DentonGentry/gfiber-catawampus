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
#
# pylint:disable=invalid-name

"""Simple real-time notifications of file changes."""

import os
import os.path
import mainloop
import pyinotify


Error = pyinotify.WatchManagerError


class FileNotifier(object):
  """A class for managing file notifications in a tornado ioloop."""

  # In some future world, there may be more than one kind of filenotifier
  # implementation (eg. if inotify isn't available).  Make our error base
  # class accessible to anyone who has an instance of our FileNotifier so
  # that they can try/except on it safely for any variant.
  Error = pyinotify.WatchManagerError

  def __init__(self, loop):
    self.loop = loop
    self.watches = {}
    self.wm = pyinotify.WatchManager()
    self.tornado_notifier = pyinotify.TornadoAsyncNotifier(
        self.wm, self.loop.ioloop)

  def __del__(self):
    n = getattr(self, 'tornado_notifier', None)
    if n:
      self.tornado_notifier.stop()

  def WatchObj(self, filename, callback):
    """Returns a filenotifier.Watch object, which calls Add() and Del()."""
    return Watch(self, filename, callback)

  def Add(self, filename, callback):
    """Register a callback for the given filename.

    Args:
      filename: the filename which, when created, deleted, or
          closed-after-write, will trigger the given callback.
      callback: the function to call whenever the file changes.
    Raises:
      pyinotify.WatchManagerError: if the containing directory does
          not exist.
    """
    path, name = os.path.split(filename)
    pathdata = self.watches.get(path, None)
    if pathdata:
      wd, files = pathdata
    else:
      files = {}

      wddict = self.wm.add_watch(
          path,
          (pyinotify.IN_CLOSE_WRITE |
           pyinotify.IN_MOVED_FROM |
           pyinotify.IN_MOVED_TO |
           pyinotify.IN_DELETE),
          lambda ev: self._Notified(ev, files),
          quiet=False)
      wd = wddict[path]
      self.watches[path] = (wd, files)
    filecalls = files.get(name, None)
    if not filecalls:
      filecalls = files[name] = []
    filecalls.append(callback)

  def Del(self, filename, callback):
    path, name = os.path.split(filename)
    wd, files = self.watches[path]
    filecalls = files[name]
    filecalls.remove(callback)
    if not filecalls:
      del files[name]
    if not files:
      self.wm.rm_watch(wd, quiet=False)
      del self.watches[path]

  def _Notified(self, ev, files):
    filecalls = files.get(ev.name, None)
    if not filecalls: return
    for i in filecalls:
      i()


class Watch(object):
  """A lifecycle handler for FileNotifier watches.

  Automatically calls filenotifier.Add and .Del when the object comes
  into and out of existence.
  """

  def __init__(self, filenotifier, filename, callback):
    self.filenotifier = filenotifier
    self.filename = filename
    self.callback = callback
    self.registered = False
    self.filenotifier.Add(self.filename, self.callback)
    self.registered = True

  def __del__(self):
    if self.registered:
      self.filenotifier.Del(self.filename, self.callback)


def main():
  def MeCall():
    print 'mecall'
  def MeCall2():
    print 'mecall2'
  def MeCall22():
    print 'mecall22'
  loop = mainloop.MainLoop()
  n = FileNotifier(loop)
  n.Add('/tmp/whatzit', MeCall)
  n.Add('/tmp/whatzit2', MeCall2)
  if not os.path.isdir('/tmp/d'):
    os.makedirs('/tmp/d')
  n.Add('/tmp/d/whatzit2', MeCall22)
  loop.Start()


if __name__ == '__main__':
  main()
