#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""The main server process for our TR-069 CPE device."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import sys
import device_info
import tr.api
import tr.bup.options
import tr.core
import tr.http
import tr.mainloop
import tr.rcommand
import tr.tornado.autoreload
import traceroute


optspec = """
runserver.py [options]
--
r,rcmd-port= TCP port to listen for rcommands on; 0 to disable [12999]
u,unix-path= Unix socket to listen on [/tmp/mainloop.sock]
p,port=      TCP port to listen for TR-069 on [7547]
ping-path=   Force CPE ping listener to this URL path (default=random)
acs-url=     URL of the TR-069 ACS server to connect to
fake-acs     Run a fake ACS (and auto-set --acs-url to that)
no-cpe       Don't run a CPE (and thus never connect to ACS)
cpe-listener Let CPE listen for http requests (not TR-069 compliant)
"""


class TemporaryRoot(tr.core.Exporter):
  """A fake class that doesn't represent any real device model at all.

  Eventually, we'll replace this with one derived from a real toplevel model
  in one of the TR docs.  We can't do that yet because we haven't implemented
  all the required objects yet.
  """

  def __init__(self, loop):
    tr.core.Exporter.__init__(self)
    self.DeviceInfo = device_info.DeviceInfo()
    self.TraceRoute = traceroute.TraceRoute(loop)
    self.Export(objects=['DeviceInfo',
                         'TraceRoute'])


def main():
  o = tr.bup.options.Options(optspec)
  (opt, flags, extra) = o.parse(sys.argv[1:])
  
  tr.tornado.autoreload.start()
  loop = tr.mainloop.MainLoop()
  root = TemporaryRoot(loop)
  if opt.rcmd_port:
    loop.ListenInet6(('', opt.rcmd_port),
                     tr.rcommand.MakeRemoteCommandStreamer(root))
  if opt.unix_path:
    loop.ListenUnix(opt.unix_path,
                    tr.rcommand.MakeRemoteCommandStreamer(root))
 
  if opt.port:
    if not opt.acs_url and not opt.fake_acs and not opt.no_cpe:
      o.fatal('You must give either --acs-url, --fake-acs, or --no-cpe.')
    acs = cpe = None
    if opt.fake_acs:
      acs = tr.api.ACS()
      if not opt.acs_url:
        opt.acs_url = 'http://localhost:%d/acs' % opt.port
    if opt.cpe:
      cpe = tr.api.CPE(acs, root)
      if opt.cpe_listener:
        tr.http.Listen(opt.port, opt.ping_path, cpe, acs)
      else:
        print 'CPE API is client mode only.'

  loop.Start()


if __name__ == '__main__':
  main()
