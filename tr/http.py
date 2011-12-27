#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import collections
import time
import random
import socket
import urllib
import api_soap
import soap
import tornadi_fix       #pylint: disable-msg=W0611
import tornado.httpclient
import tornado.ioloop
import tornado.web


Url = collections.namedtuple('Url', ('method host port path'))


def SplitUrl(url):
    method, rest = urllib.splittype(url)
    hostport, path = urllib.splithost(rest)
    host, port = urllib.splitport(hostport)
    return Url(method, host, int(port or 0), path)


# TODO(apenwarr): We should never do http synchronously.
# ...because it'll freeze our app while it runs.  But this is easier than
# doing async callbacks for now.
def SyncClient(url, postdata):
  """HTTP POST the given postdata to the given url, returning the result."""
  cli = tornado.httpclient.HTTPClient()
  postdata = str(postdata)
  if postdata:
    headers = { 'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': '' }
  else:
    headers = {}
  req = tornado.httpclient.HTTPRequest(url=url, method="POST",
                                       headers=headers, body=postdata,
                                       allow_ipv6=True)
  result = cli.fetch(req)
  return result.body


class PingHandler(tornado.web.RequestHandler):
  def initialize(self, callback):
    self.callback = callback

  def get(self):
    self.callback()


class Handler(tornado.web.RequestHandler):
  def initialize(self, soap_handler):
    self.soap_handler = soap_handler

  def get(self):
    self.write("This is the cpe/acs handler.  It only takes POST requests.")

  def post(self):
    print 'TR-069 server: request received:\n%s' % self.request.body
    if self.request.body.strip():
      result = self.soap_handler(self.request.body)
      self.write(str(result))


class CPEStateMachine(object):
  def __init__(self, ip, cpe, listenport, acs_url, ping_path):
    self.cpe = cpe
    self.listenport = listenport
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.acs_url = acs_url
    self.ping_path = ping_path
    self.encode = api_soap.Encode()
    self.response_queue = []
    self.request_queue = []
    self.on_hold = False  # TODO(apenwarr): actually set this somewhere
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.http = tornado.httpclient.AsyncHTTPClient(io_loop=self.ioloop)
    self.cookies = None
    self.my_configured_ip = ip
    self.my_ip = None

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def _GetLocalAddr(self):
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    # If not configured with an address it gets a bit tricky: we try connecting
    # to the ACS, non-blocking, so we can find out which local IP the kernel
    # uses when connecting to that IP.  The local address is returned with
    # getsockname(). Then we can tell the ACS to use that address for
    # connecting to us later.  We use a nonblocking socket because we don't
    # care about actually connecting; we just care what the local kernel does
    # in its implicit bind() when we *start* connecting.
    assert self.acs_url
    url = SplitUrl(self.acs_url)
    host = url.host
    port = url.port or 0
    s = socket.socket()
    s.setblocking(0)
    try:
      s.connect((host, port or 1))  # port doesn't matter, but can't be 0
    except socket.error, e:
      pass
    return s.getsockname()[0]

  def SendInform(self, reason):
    if not self.my_ip:
      self.my_ip = self._GetLocalAddr()
    events = [(reason, '')]
    parameter_list = []
    if self.ping_path:
      di = self.cpe.root.DeviceInfo
      parameter_list += [
          ('Device.ManagementServer.ConnectionRequestURL',
           'http://%s:%d/%s' % (self.my_ip, self.listenport, self.ping_path)),
          ('Device.DeviceInfo.HardwareVersion', di.HardwareVersion),
          ('Device.DeviceInfo.SoftwareVersion', di.SoftwareVersion),
      ]
    req = self.encode.Inform(root=self.cpe.root,
                             events=events,
                             max_envelopes=1, current_time=None,
                             retry_count=1, parameter_list=parameter_list)
    return self.Send(req)

  def SendDownloadResponse(self, command_key, starttime, endtime):
    resp = self.encode.DownloadResponse(command_key, starttime, endtime)
    return self.Send(resp)

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime):
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    return self.Send(cmpl)

  def GetNext(self):
    if self.response_queue:
      return self.response_queue.pop(0)
    elif self.request_queue and not self.on_hold:
      return self.request_queue.pop(0)

  def Run(self):
    print 'RUN'
    nextmsg = self.GetNext()
    headers = {}
    if self.cookies:
      headers['Cookie'] = ";".join(self.cookies)
    if nextmsg:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      nextmsg = ''
    print "CPE POST: %r\n%s" % (str(headers), nextmsg)
    req = tornado.httpclient.HTTPRequest(url=self.acs_url, method="POST",
                                         headers=headers, body=nextmsg,
                                         allow_ipv6=True)
    self.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
    print 'CPE RECEIVED (at %s):' % time.ctime()
    if not response.error:
      cookies = response.headers.get_list("Set-Cookie")
      if cookies:
        self.cookies = cookies
      print response.body
      if response.body:
        out = self.cpe_soap.Handle(response.body)
        if out is not None:
          self.Send(out)
          self.Run()
    else:
      print('HTTP ERROR Code %d' % response.code)
    if (self.response_queue or
        (self.request_queue and not self.on_hold)):
      self.Run()

  def _CleanUpForNewSession(self):
    self.cookies = None
    self.my_ip = None

  def PingReceived(self):
    self._CleanUpForNewSession()
    self.SendInform('6 CONNECTION REQUEST')


def Listen(ip, port, ping_path, acs, acs_url, cpe, cpe_listener):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  cpe_machine = CPEStateMachine(ip, cpe, port, acs_url, ping_path)
  cpe.SetDownloadCalls(cpe_machine.SendDownloadResponse,
                       cpe_machine.SendTransferComplete)
  handlers = []
  if acs:
    acshandler = api_soap.ACS(acs).Handle
    handlers.append(('/acs', Handler, dict(soap_handler=acshandler)))
    print 'TR-069 ACS at http://*:%d/acs' % port
  if cpe and cpe_listener:
    cpehandler = cpe_machine.cpe_soap.Handle
    handlers.append(('/cpe', Handler, dict(soap_handler=cpehandler)))
    print 'TR-069 CPE at http://*:%d/cpe' % port
  if ping_path:
    handlers.append(('/' + ping_path, PingHandler,
                     dict(callback=cpe_machine.PingReceived)))
    print 'TR-069 callback at http://*:%d/%s' % (port, ping_path)
  webapp = tornado.web.Application(handlers)
  webapp.listen(port)
  cpe_machine.SendInform('0 BOOTSTRAP')


def main():
  with soap.Envelope(1234, False) as xml:
    soap.GetParameterNames(xml, '', True)
    #xml.GetRPCMethods(None)
  print 'Response:'
  print SyncClient('http://localhost:7547/cpe', xml)


if __name__ == '__main__':
  main()
