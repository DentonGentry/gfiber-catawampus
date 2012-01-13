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
import cpe_management_server
import cwmpbool
import cwmpdate
import cwmp_session
import time
import random
import socket
import urllib
import api_soap
import soap
import tornado.httpclient
import tornado.ioloop
import tornado.web


# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf

def SplitUrl(url):
  Url = collections.namedtuple('Url', ('method host port path'))
  method, rest = urllib.splittype(url)
  hostport, path = urllib.splithost(rest)
  host, port = urllib.splitport(hostport)
  return Url(method, host, int(port or 0), path)


class PingHandler(tornado.web.RequestHandler):
  # TODO $SPEC3 3.2.2 "The CPE MUST use HTTP digest authentication"
  #   see https://github.com/bkjones/curtain for Tornado digest auth mixin
  # TODO $SPEC3 3.2.2 "The CPE SHOULD restrict the number of Connection
  #   Requests it accepts during a given period of time..."
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
    ip: local ip address to bind to. If None, find address automatically.
    cpe: the api_soap.cpe object for this device
    listenport: the port number to listen on for ACS ping requests.
    acs_url_file: A file which will contain the ACS URL. This file can
      change during operation, and must be periodically re-read.
    ping_path: URL path for the ACS Ping function
  """
  def __init__(self, ip, cpe, listenport, acs_url_file, ping_path, ioloop=None):
    self.cpe = cpe
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.encode = api_soap.Encode()
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.event_queue = []
    self.inform = None
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.retry_count = 0  # for Inform.RetryCount
    self.session = None
    self.my_configured_ip = ip
    self.cpe_management_server = cpe_management_server.CpeManagementServer(
        acs_url_file=acs_url_file, port=listenport, ping_path=ping_path,
        get_parameter_key=cpe.GetParameterKey, start_session=self.StartSession,
        ioloop=self.ioloop)

  def GetManagementServer(self):
    """Return the ManagementServer implementation for tr-98/181."""
    return self.cpe_management_server

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def SendResponse(self, req):
    self.response_queue.append(str(req))
    self.Run()

  def _GetLocalAddr(self):
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    acs_url = self.cpe_management_server.URL
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
      my_ip = self._GetLocalAddr()
      self.session.my_ip = my_ip
      self.cpe_management_server.my_ip = my_ip
    events = [(reason, '')]
    for ev in self.event_queue:
      events.append(ev)
    parameter_list = []
    # TODO(dgentry) interrogate root to look for Device or InternetGatewayDevice
    di = self.cpe.root.GetExport('Device.DeviceInfo')
    parameter_list += [
        ('Device.ManagementServer.ConnectionRequestURL',
         self.cpe_management_server.ConnectionRequestURL),
        ('Device.DeviceInfo.HardwareVersion', di.HardwareVersion),
        ('Device.DeviceInfo.SoftwareVersion', di.SoftwareVersion),
    ]
    req = self.encode.Inform(root=self.cpe.root, events=events,
                             retry_count=self.retry_count,
                             parameter_list=parameter_list)
    self.inform = str(req)
    self.Run()

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime, event_code):
    self.event_queue.append((event_code, command_key))
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    self.Send(cmpl)

  def GetNext(self):
    if not self.session:
      return None
    if self.session.inform_required():
      if self.inform:
        self.session.state_update(sent_inform=True)
        inform = self.inform
        self.inform = None
        return inform
    if self.response_queue and self.session.response_allowed():
      return self.response_queue.pop(0)
    if self.request_queue and self.session.request_allowed():
      return self.request_queue.pop(0)
    return ''

  def Run(self):
    print 'RUN'
    if not self.session:
      print('No ACS session, returning.')
      return
    acs_url = self.session.acs_url
    if not acs_url:
      print('No ACS URL populated yet, returning.')
      return
    if self.session.should_close():
      print('Idle CWMP session, terminating.')
      self.outstanding = None
      if self.session.close():
        # Ping received during session, start another
        self.ioloop.add_callback(self._NewPingSession)
      self.session = None
      self.retry_count = 0  # Successful close
      return

    if self.outstanding is not None:
      # already an outstanding request
      return
    if self.outstanding is None:
      self.outstanding = self.GetNext()
    if self.outstanding is None:
      # We're not allowed to send anything yet, session not fully open.
      return

    headers = {}
    if self.session.cookies:
      headers['Cookie'] = ";".join(self.session.cookies)
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      # Empty message
      self.session.state_update(cpe_to_acs_empty=True)
    print("CPE POST (at {0!s}):\n{1!s}\n{2!s}".format(
        time.ctime(), headers, self.outstanding))
    req = tornado.httpclient.HTTPRequest(
        url=acs_url, method="POST", headers=headers,
        body=self.outstanding, follow_redirects=True, max_redirects=5,
        request_timeout=30.0, use_gzip=True, allow_ipv6=True,
        user_agent="catawampus-tr69")
    self.session.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
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
        self.session.state_update(acs_to_cpe_empty=True)
    else:
      print('HTTP ERROR Code %d' % response.code)
      if self.session.close():
        # Ping received during session, start another
        self.ioloop.add_callback(self._NewPingSession)
      self.session = None
      self.retry_count += 1
    self.Run()
    return 200

  def _NewTransferCompleteSession(self):
    if not self.session:
      self.session = cwmp_session.CwmpSession(self.cpe_management_server.URL,
                                              self.ioloop)
      self.SendInform('7 TRANSFER COMPLETE')

  def _NewPingSession(self):
    if not self.session:
      self.session = cwmp_session.CwmpSession(self.cpe_management_server.URL,
                                              self.ioloop)
      self.SendInform('6 CONNECTION REQUEST')
    else:
      # $SPEC3 3.2.2 initiate at most one new session after this one closes.
      self.session.ping_received = True

  def StartSession(self, event_code, event_queue=None):
    if not self.session:
      if event_queue:
        self.event_queue.extend(event_queue)
      self.session = cwmp_session.CwmpSession(self.cpe_management_server.URL,
                                              self.ioloop)
      self.SendInform(event_code)

  def PingReceived(self):
    # $SPEC3 3.2.2: CPE MUST respond immediately, before initiating session.
    self.ioloop.add_callback(self._NewPingSession)
    return 204  # No Content

  def TransferCompleteReceived(self):
    for ev in self.event_queue:
      xfer_reasons = frozenset(['m download', 'm scheduledownload', 'm upload'])
      (reason, command_key) = ev
      if reason.lower() in xfer_reasons:
        self.event_queue.remove(ev)

  def InformResponseReceived(self):
    for ev in self.event_queue:
      inform_reasons = frozenset(['m reboot', 'm scheduleinform'])
      (reason, command_key) = ev
      if reason.lower() in inform_reasons:
        self.event_queue.remove(ev)

  def Startup(self):
    self.session = cwmp_session.CwmpSession(self.cpe_management_server.URL,
                                            self.ioloop)
    # TODO(dgentry) Check whether we have a config, send '1 BOOT' instead
    self.cpe.Startup()
    self.SendInform('0 BOOTSTRAP')


def Listen(ip, port, ping_path, acs, acs_url_file, cpe, cpe_listener):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  cpe_machine = CPEStateMachine(ip, cpe, port, acs_url_file, ping_path)
  cpe.SetCallbacks(cpe_machine.SendTransferComplete,
                   cpe_machine.TransferCompleteReceived,
                   cpe_machine.InformResponseReceived)
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
