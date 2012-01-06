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


# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf

Url = collections.namedtuple('Url', ('method host port path'))


def SplitUrl(url):
    method, rest = urllib.splittype(url)
    hostport, path = urllib.splithost(rest)
    host, port = urllib.splitport(hostport)
    return Url(method, host, int(port or 0), path)


class CwmpSession(object):
  def __init__(self, io_loop=None):
    self.http = tornado.httpclient.AsyncHTTPClient(
        max_simultaneous_connections=1,
        io_loop=io_loop or tornado.ioloop.IOLoop.instance())
    self.cookies = None
    self.my_ip = None
    self.no_more_requests = False
    self.acs_empty = False
    self.on_hold = False
    self.ping_received = False

  def __del__(self):
    self.close()

  def close(self):
    self.http = None
    return self.ping_received


class PingHandler(tornado.web.RequestHandler):
  # TODO $SPEC3 3.2.2 "The CPE MUST use HTTP digest authentication"
  # TODO $SPEC3 3.2.2 "The CPE SHOULD restrict the number of Connection Requests it
  #   accepts during a given period of time..."
  def initialize(self, callback):
    self.callback = callback

  def get(self):
    self.set_status(self.callback())


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
  """A tr-69 Customer Premises Equipment implementation.

  Args:
    ip: local ip address to bind to. If None, figure out address to use automatically.
    cpe: the api_soap.cpe object for this device
    listenport: the port number to listen on for ACS ping requests.
    acs_url_file: A file which will contain the ACS URL. This file can
      change during operation, and must be periodically re-read.
    ping_path: URL path for the ACS Ping function
  """
  def __init__(self, ip, cpe, listenport, acs_url_file, ping_path):
    self.cpe = cpe
    self.listenport = listenport
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.acs_url_file = acs_url_file
    self.ping_path = ping_path
    self.encode = api_soap.Encode()
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.session = None
    self.my_configured_ip = ip

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def SendResponse(self, req):
    self.response_queue.append(str(req))
    self.Run()

  def _GetAcsUrl(self):
    try:
      f = open(self.acs_url_file, "r")
      line = f.readline().strip()
      f.close()
    except IOError:
      line = ''
    return line

  def _GetLocalAddr(self):
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    acs_url = self._GetAcsUrl()
    if not acs_url:
      return 0

    # If not configured with an address it gets a bit tricky: we try connecting
    # to the ACS, non-blocking, so we can find out which local IP the kernel
    # uses when connecting to that IP.  The local address is returned with
    # getsockname(). Then we can tell the ACS to use that address for
    # connecting to us later.  We use a nonblocking socket because we don't
    # care about actually connecting; we just care what the local kernel does
    # in its implicit bind() when we *start* connecting.
    url = SplitUrl(acs_url)
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
    if not self.session.my_ip:
      self.session.my_ip = self._GetLocalAddr()
    events = [(reason, '')]
    parameter_list = []
    if self.ping_path:
      di = self.cpe.root.DeviceInfo
      parameter_list += [
          ('Device.ManagementServer.ConnectionRequestURL',
           'http://%s:%d/%s' % (self.session.my_ip, self.listenport,
                                self.ping_path)),
          ('Device.DeviceInfo.HardwareVersion', di.HardwareVersion),
          ('Device.DeviceInfo.SoftwareVersion', di.SoftwareVersion),
      ]
    req = self.encode.Inform(root=self.cpe.root,
                             events=events,
                             max_envelopes=1,
                             retry_count=1, parameter_list=parameter_list)
    return self.Send(req)

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime):
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    return self.Send(cmpl)

  def GetNext(self):
    if self.response_queue:
      return self.response_queue.pop(0)
    elif self.request_queue and not self.session.on_hold and not self.session.no_more_requests:
      return self.request_queue.pop(0)

  def Run(self):
    print 'RUN'
    if not self.session:
      return
    acs_url = self._GetAcsUrl()
    if not acs_url:
      print('No ACS URL populated yet, returning.')
      return
    if self.session.no_more_requests and self.session.acs_empty:
      print('Idle CWMP session, terminating.')
      self.outstanding = None
      if self.session.close():
        # Ping received during session, start another
        self.ioloop.add_callback(self._NewPingSession)
      self.session = None
      return

    if self.outstanding is None:
      self.outstanding = self.GetNext()
    else:
      # already an outstanding request
      return
    headers = {}
    if self.session.cookies:
      headers['Cookie'] = ";".join(self.session.cookies)
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      self.outstanding = ''
      self.session.no_more_requests = True  # $SPEC3 3.7.1.3
    print "CPE POST: %r\n%s" % (str(headers), self.outstanding)
    req = tornado.httpclient.HTTPRequest(url=acs_url, method="POST",
                                         headers=headers, body=self.outstanding,
                                         follow_redirects=True,
                                         max_redirects=5,  # $SPEC3 3.4.2
                                         request_timeout=30.0,
                                         use_gzip=True, allow_ipv6=True)
    self.session.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
    was_outstanding = self.outstanding
    self.outstanding = None
    print 'CPE RECEIVED (at %s):' % time.ctime()
    if not self.session:
      print 'Session terminated, ignoring ACS message.'
      return
    if not response.error:
      cookies = response.headers.get_list("Set-Cookie")
      if cookies:
        self.session.cookies = cookies
      print response.body
      if response.body:
        out = self.cpe_soap.Handle(response.body)
        if out is not None:
          self.SendResponse(out)
      else:
        self.session.acs_empty = True
    else:
      print('HTTP ERROR Code %d' % response.code)
      if self.session.close():
        # Ping received during session, start another
        self.ioloop.add_callback(self._NewPingSession)
      self.session = None
    if (was_outstanding or
        self.response_queue or
        (self.request_queue and not self.session.on_hold)):
      self.Run()

  def _NewPingSession(self):
    if not self.session:
      self.session = CwmpSession(self.ioloop)
      self.SendInform('6 CONNECTION REQUEST')
    else:
      # $SPEC3 3.2.2 initiate at most one new session after this one closes.
      self.session.ping_received = True

  def PingReceived(self):
    # $SPEC3 3.2.2: CPE MUST respond immediately, before initiating session.
    self.ioloop.add_callback(self._NewPingSession)
    return 204  # No Content

  def Bootstrap(self):
    self.session = CwmpSession(self.ioloop)
    self.SendInform('0 BOOTSTRAP')


def Listen(ip, port, ping_path, acs, acs_url_file, cpe, cpe_listener):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  cpe_machine = CPEStateMachine(ip, cpe, port, acs_url_file, ping_path)
  cpe.SetDownloadCalls(cpe_machine.SendTransferComplete)
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
  return cpe_machine


def main():
  with soap.Envelope(1234, False) as xml:
    soap.GetParameterNames(xml, '', True)
    #xml.GetRPCMethods(None)
  print 'Response:'
  print SyncClient('http://localhost:7547/cpe', xml)


if __name__ == '__main__':
  main()
