#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import binascii
import collections
import random
import socket
import time
import urllib

import tornado.httpclient
import tornado.ioloop
import tornado.web

import api_soap
import cpe_management_server
import cwmp_session
import soap

PROC_IF_INET6 = '/proc/net/if_inet6'


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
    self.write('This is the cpe/acs handler.  It only takes POST requests.')

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
    ping_ip6dev: ifname to use for the CPE Ping address.
    fetch_args: kwargs to pass to HTTPClient.fetch
  """
  def __init__(self, ip, cpe, listenport, acs_url_file, ping_path,
               ping_ip6dev=None, fetch_args=dict(), ioloop=None):
    self.cpe = cpe
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.encode = api_soap.Encode()
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.event_queue = []
    self.inform_reason = None
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.retry_count = 0  # for Inform.RetryCount
    self.start_session_timeout = None  # timer for CWMPRetryInterval
    self.session = None
    self.my_configured_ip = ip
    self.ping_ip6dev = ping_ip6dev
    self.fetch_args = fetch_args
    self.cpe_management_server = cpe_management_server.CpeManagementServer(
        acs_url_file=acs_url_file, port=listenport, ping_path=ping_path,
        get_parameter_key=cpe.getParameterKey,
        start_periodic_session=self.NewPeriodicSession, ioloop=self.ioloop)

  def GetManagementServer(self):
    """Return the ManagementServer implementation for tr-98/181."""
    return self.cpe_management_server

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def SendResponse(self, req):
    self.response_queue.append(str(req))
    self.Run()

  def LookupDevIP6(self, name):
    """Returns the global IPv6 address for the named interface."""
    with open(PROC_IF_INET6, 'r') as f:
      for line in f:
        fields = line.split()
        if len(fields) < 6:
          continue
        scope = int(fields[3].strip())
        dev = fields[5].strip()
        if dev == name and scope == 0:
          bin_ip = binascii.unhexlify(fields[0])
          return socket.inet_ntop(socket.AF_INET6, bin_ip)
    return 0

  def _GetLocalAddr(self):
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    if self.ping_ip6dev is not None:
      return self.LookupDevIP6(self.ping_ip6dev)
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

  def EncodeInform(self):
    """Return an Inform message for this session."""
    if not self.session.my_ip:
      my_ip = self._GetLocalAddr()
      self.session.my_ip = my_ip
      self.cpe_management_server.my_ip = my_ip
    events = [(self.inform_reason, None)]
    for ev in self.event_queue:
      events.append(ev)
    parameter_list = []
    try:
      ms = self.cpe.root.GetExport('InternetGatewayDevice.ManagementServer')
      di = self.cpe.root.GetExport('InternetGatewayDevice.DeviceInfo')
      parameter_list += [
          ('InternetGatewayDevice.ManagementServer.ConnectionRequestURL',
           ms.ConnectionRequestURL),
          ('InternetGatewayDevice.ManagementServer.ParameterKey',
           ms.ParameterKey),
          ('InternetGatewayDevice.DeviceInfo.HardwareVersion',
           di.HardwareVersion),
          ('InternetGatewayDevice.DeviceInfo.SoftwareVersion',
           di.SoftwareVersion),
          ('InternetGatewayDevice.DeviceInfo.SpecVersion', di.SpecVersion),
      ]
    except (AttributeError, KeyError):
      pass
    req = self.encode.Inform(root=self.cpe.root, events=events,
                             retry_count=self.retry_count,
                             parameter_list=parameter_list)
    return str(req)

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime, event_code):
    # TODO(dgentry) need to initiate a session reason '7 TRANSFER COMPLETE'
    self.event_queue.append((event_code, command_key))
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    self.Send(cmpl)

  def GetNext(self):
    if not self.session:
      return None
    if self.session.inform_required():
      self.session.state_update(sent_inform=True)
      return self.EncodeInform()
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
    if not self.session.acs_url:
      print('No ACS URL populated, returning.')
      self._ScheduleRetrySession(wait=60)
      return
    if self.session.should_close():
      print('Idle CWMP session, terminating.')
      self.outstanding = None
      if self.session.close():
        # Ping received during session, start another
        self._NewPingSession()
      self.session = None
      self.retry_count = 0  # Successful close
      self.inform_reason = None
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
      headers['Cookie'] = ';'.join(self.session.cookies)
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      # Empty message
      self.session.state_update(cpe_to_acs_empty=True)
    print('CPE POST (at {0!s}):\n'
          'ACS URL: {1!r}\n'
          '{2!s}\n'
          '{3!s}'.format(time.ctime(), self.session.acs_url,
                         headers, self.outstanding))
    req = tornado.httpclient.HTTPRequest(
        url=self.session.acs_url, method='POST', headers=headers,
        body=self.outstanding, follow_redirects=True, max_redirects=5,
        request_timeout=30.0, use_gzip=True, allow_ipv6=True,
        **self.fetch_args)
    self.session.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
    self.outstanding = None
    print 'CPE RECEIVED (at %s):' % time.ctime()
    if not self.session:
      print 'Session terminated, ignoring ACS message.'
      return
    if not response.error:
      cookies = response.headers.get_list('Set-Cookie')
      if cookies:
        self.session.cookies = cookies
      print response.body
      if response.body:
        out = self.cpe_soap.Handle(response.body)
        if out is not None:
          self.SendResponse(out)
        # TODO(dgentry): $SPEC3 3.7.1.6 ACS Fault 8005 == retry same request
      else:
        self.session.state_update(acs_to_cpe_empty=True)
    else:
      print('HTTP ERROR {0!s}: {1}'.format(response.code, response.error))
      self._ScheduleRetrySession()
    self.Run()
    return 200

  def _ScheduleRetrySession(self, wait=None):
    """Start a timer to retry a CWMP session.

    Args:
      wait - number of seconds to wait. If wait=None, choose a random wait
        time according to $SPEC3 section 3.2.1
    """
    if self.session:
      self.session.close()
      self.session = None
    if wait is None:
      self.retry_count += 1
      wait = self.cpe_management_server.SessionRetryWait(self.retry_count)
    timeout = time.time() + wait
    self.start_session_timeout = self.ioloop.add_timeout(
        timeout, self._SessionWaitTimer)

  def _SessionWaitTimer(self):
    """Handler for the CWMP Retry timer, to start a new session."""
    self.start_session_timeout = None
    self.session = cwmp_session.CwmpSession(
        acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
    self.Run()

  def _CancelSessionRetries(self):
    """Cancel any pending CWMP session retry."""
    if self.start_session_timeout:
      self.ioloop.remove_timeout(self.start_session_timeout)
      self.start_session_timeout = None
    self.retry_count = 0

  def _NewSession(self, reason):
    if not self.session:
      self._CancelSessionRetries()
      self.inform_reason = reason
      self.session = cwmp_session.CwmpSession(
          acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
      self.Run()

  def _NewPingSession(self):
    if not self.session:
      self._NewSession('6 CONNECTION REQUEST')
    else:
      # $SPEC3 3.2.2 initiate at most one new session after this one closes.
      self.session.ping_received = True

  def NewPeriodicSession(self):
    self._NewSession('2 PERIODIC')

  def PingReceived(self):
    self._NewPingSession()
    return 204  # No Content

  def TransferCompleteReceived(self):
    """Called when the ACS sends a TransferCompleteResponse."""
    xfer_reasons = frozenset(['m download', 'm scheduledownload', 'm upload'])
    for ev in self.event_queue:
      (reason, command_key) = ev
      if reason.lower() in xfer_reasons:
        self.event_queue.remove(ev)

  def InformResponseReceived(self):
    """Called when the ACS sends an InformResponse."""
    inform_reasons = frozenset(['m reboot', 'm scheduleinform'])
    for ev in self.event_queue:
      (reason, command_key) = ev
      if reason.lower() in inform_reasons:
        self.event_queue.remove(ev)

  def Startup(self):
    self._NewSession('0 BOOTSTRAP')
    # TODO(dgentry) Check whether we have a config, send '1 BOOT' instead
    self.cpe.startup()


def Listen(ip, port, ping_path, acs, acs_url_file, cpe, cpe_listener,
           ping_ip6dev=None, fetch_args=dict(), ioloop=None):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  cpe_machine = CPEStateMachine(ip=ip, cpe=cpe, listenport=port,
                                acs_url_file=acs_url_file, ping_path=ping_path,
                                ping_ip6dev=ping_ip6dev, fetch_args=fetch_args,
                                ioloop=ioloop)
  cpe.setCallbacks(cpe_machine.SendTransferComplete,
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
