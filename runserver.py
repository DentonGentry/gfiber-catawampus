#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""The main server process for our TR-069 CPE device."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import device_info
import tr.core
import tr.mainloop
import tr.rcommand
import tr.tornado.autoreload
import traceroute


class Root(tr.core.Exporter):
  """A fake class that doesn't represent any real device model at all.

  Eventually, we'll replace this with one derived from a real toplevel model
  in one of the TR docs.
  """

  def __init__(self, loop):
    tr.core.Exporter.__init__(self)
    self.DeviceInfo = device_info.DeviceInfo()
    self.TraceRoute = traceroute.TraceRoute(loop)
    self.Export(objects=['DeviceInfo',
                         'TraceRoute'])


def main():
  tr.tornado.autoreload.start()
  loop = tr.mainloop.MainLoop()
  root = Root(loop)
  loop.ListenInet6(('', 12999),
                   tr.rcommand.MakeRemoteCommandStreamer(root))
  loop.ListenUnix('/tmp/mainloop.sock',
                  tr.rcommand.MakeRemoteCommandStreamer(root))
  loop.Start()


if __name__ == '__main__':
  main()
