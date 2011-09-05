#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""The main server process for our TR-069 CPE device."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import device_info
import tr.mainloop
import tr.rcommand  #pylint: disable-msg=W0404


def main():
  loop = tr.mainloop.MainLoop()
  root = device_info.DeviceInfo()
  loop.ListenInet6(('', 12999),
                   tr.rcommand.MakeRemoteCommandStreamer(root))
  loop.ListenUnix('/tmp/mainloop.sock',
                  tr.rcommand.MakeRemoteCommandStreamer(root))
  loop.Start()


if __name__ == '__main__':
  main()
