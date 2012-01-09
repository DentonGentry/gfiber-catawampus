#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""The main server process for our TR-069 CPE device."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import dm.catawampus
import dm.management_server
import imp
import os.path
import sys
import tempfile
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
r,rcmd-port=  TCP port to listen for rcommands on; 0 to disable [12999]
u,unix-path=  Unix socket to listen on [/tmp/mainloop.sock]
i,ip=         IP address to report to ACS. (default=finds interface IP address)
p,port=       TCP port to listen for TR-069 on [7547]
ping-path=    Force CPE ping listener to this URL path (default=random)
acs-url=      URL of the TR-069 ACS server to connect to (deprecated)
acs-url-file= Filename where ACS URL should be read from
fake-acs      Run a fake ACS (and auto-set --acs-url to that)
no-cpe        Don't run a CPE (and thus never connect to ACS)
cpe-listener  Let CPE listen for http requests (not TR-069 compliant)
platform=     Activate the platform-specific device tree
"""


class DeviceModelRoot(tr.core.Exporter):
  """A class to hold the device models."""

  def __init__(self, loop, platform):
    tr.core.Exporter.__init__(self)
    if platform:
      path = os.path.join('platform', platform, 'device.py')
      device = imp.load_source('device', path)
      (params, objects) = device.PlatformInit(name=platform,
                                              device_model_root=self)
    else:
      (params, objects) = (list(), list())
    self.TraceRoute = traceroute.TraceRoute(loop)
    objects.append('TraceRoute')
    self.X_CATAWAMPUS_ORG_CATAWAMPUS = dm.catawampus.CatawampusDm()
    objects.append('X_CATAWAMPUS-ORG_CATAWAMPUS')
    self.Export(params=params, objects=objects)

  def add_management_server(self, mgmt):
    # tr-181 Device.ManagementServer
    try:
      ms181 = self.GetExport('Device')
      ms181.ManagementServer = dm.management_server.ManagementServer181(mgmt)
    except AttributeError:
      pass  # no tr-181 for this platform

    # tr-98 InternetGatewayDevice.ManagementServer
    try:
      ms98 = self.GetExport('InternetGatewayDevice')
      ms98.ManagementServer = dm.management_server.ManagementServer98(mgmt)
    except AttributeError:
      pass  # no tr-98 for this platform


def _WriteAcsFile(acs_url):
  acsfile = tempfile.NamedTemporaryFile(prefix='acsurl', delete=False)
  acsfile.write(acs_url)
  acsfile.close()
  return acsfile.name

def main():
  o = tr.bup.options.Options(optspec)
  (opt, flags, extra) = o.parse(sys.argv[1:])

  #tr.tornado.httpclient.AsyncHTTPClient.configure("tr.tornado.curl_httpclient.CurlAsyncHTTPClient")
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
    acs_url_present = opt.acs_url or opt.acs_url_file
    if not acs_url_present and not opt.fake_acs and not opt.no_cpe:
      o.fatal('You must give either --acs-url-file, --fake-acs, or --no-cpe.')
    acs = cpe = None
    if opt.fake_acs:
      acs = tr.api.ACS()
      if not opt.acs_url:
        opt.acs_url = 'http://localhost:%d/acs' % opt.port
    if opt.cpe:
      cpe = tr.api.CPE(root)
      if not opt.cpe_listener:
        print 'CPE API is client mode only.'
    if opt.acs_url_file:
      acs_url_file = opt.acs_url_file
    elif opt.acs_url:
      acs_url_file = _WriteAcsFile(opt.acs_url)
    else:
      acs_url_file = _WriteAcsFile('')

    cpe_machine = tr.http.Listen(opt.ip, opt.port, opt.ping_path, acs,
                                 acs_url_file, cpe, cpe and opt.cpe_listener)
    root.add_management_server(cpe_machine.GetManagementServer())
    cpe_machine.Bootstrap()

  loop.Start()


if __name__ == '__main__':
  print
  main()
