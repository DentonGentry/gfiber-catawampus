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
i,ip=        IP address to report to ACS. (default=finds interface IP address)
p,port=      TCP port to listen for TR-069 on [7547]
ping-path=   Force CPE ping listener to this URL path (default=random)
acs-url=     URL of the TR-069 ACS server to connect to
fake-acs     Run a fake ACS (and auto-set --acs-url to that)
no-cpe       Don't run a CPE (and thus never connect to ACS)
cpe-listener Let CPE listen for http requests (not TR-069 compliant)
platform=    Activate the platform-specific device tree
"""


class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform):
    tr.core.Exporter.__init__(self)
    if platform == "gfmedia":
      import platform.gfmedia.device as device
      (params, objects) = device.PlatformInit(name='gfmedia',
                                              device_model_root=self)
    else:
      import platform.fakecpe.device as device
      (params, objects) = device.PlatformInit(name='fakecpe',
                                              device_model_root=self)
    self.Foo = 'bar'
    params.append('Foo')
    self.TraceRoute = traceroute.TraceRoute(loop)
    objects.append('TraceRoute')
    self.Export(params=params, objects=objects)


def main():
  o = tr.bup.options.Options(optspec)
  (opt, flags, extra) = o.parse(sys.argv[1:])

  tr.tornado.autoreload.start()
  loop = tr.mainloop.MainLoop()
  root = DeviceModelRoot(loop, opt.platform)
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
      if not opt.cpe_listener:
        print 'CPE API is client mode only.'
    tr.http.Listen(opt.ip, opt.port, opt.ping_path, acs, opt.acs_url,
                   cpe, cpe and opt.cpe_listener)

  loop.Start()


if __name__ == '__main__':
  print
  main()
