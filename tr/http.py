#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import binascii
import collections
import datetime
import os
import random
import socket
import sys
import time
import urllib

from curtain import digest
import helpers
import pycurl
import tornado.httpclient
import tornado.ioloop
import tornado.util
import tornado.web

import api_soap
import cpe_management_server
import cwmplog
import monohelper
import session
import filenotifier
import mainloop
import pyinotify


PROC_IF_INET6 = '/proc/net/if_inet6'
MAX_EVENT_QUEUE_SIZE = 64
GETWANPORT = 'activewan'
CWMP_TMPDIR = '/tmp/cwmp'
DISABLE_ACS_FILE = 'disable_acs'
ACS_DISABLE_EXPIRY_SECS = 10 * 60

Url = collections.namedtuple('Url', ('method host port path'))


class LimitDeque(collections.deque):
  """Wrapper around a deque that limits the maximimum size.

  If the maximum size is reached, call the supplied handler, or
  exit if no handler is provided.
  """

  def __init__(self, max_size=None, handler=None):
    collections.deque.__init__(self)
    self.max_size = max_size
    self.handler = handler

  def CheckSize(self):
    if self.max_size and len(self) > self.max_size:
      if self.handler:
        self.handler()
      else:
        print 'Maximum length of deque (%d) was exceeded' % (self.max_size)
        sys.exit(1)

  def append(self, *args):
    collections.deque.append(self, *args)
    self.CheckSize()

  def appendleft(self, *args):
    collections.deque.appendleft(self, *args)
    self.CheckSize()

  def extend(self, *args):
    collections.deque.extend(self, *args)
    self.CheckSize()

  def extendleft(self, *args):
    collections.deque.extendleft(self, *args)
    self.CheckSize()


# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf
def SplitUrl(url):
  method, rest = urllib.splittype(url)
  hostport, path = urllib.splithost(rest)
  host, port = urllib.splitport(hostport)
  return Url(method, host, int(port or 0), path)


class PingHandler(digest.DigestAuthMixin, tornado.web.RequestHandler):
  """Handles accesses to the ConnectionRequestURL.

  Args:
    callback: the function to call when theURL is accessed.
    cpe_ms: the cpe_management_server object, from which to retrieve
      username and password.
  """

  def initialize(self, callback, cpe_ms):
    self.callback = callback
    self.cpe_ms = cpe_ms

  def getcredentials(self, username):
    credentials = {'auth_username': self.cpe_ms.ConnectionRequestUsername,
                   'auth_password': self.cpe_ms.ConnectionRequestPassword}
    if username == credentials['auth_username']:
      return credentials

  def get(self):
    # Digest authentication handler
    if self.get_authenticated_user(self.getcredentials, 'Authusers'):
      return self.set_status(self.callback())


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


REDIRECT_ON_301 = 1
REDIRECT_ON_302 = 2


def CurlCreator(oldcreator, *args, **kwargs):
  """Set some pycurl options that tornado doesn't otherwise use."""
  curl = oldcreator(*args, **kwargs)
  curl.setopt(pycurl.POST301, REDIRECT_ON_301 | REDIRECT_ON_302)
  return curl


class CPEStateMachine(object):
  """A tr-69 Customer Premises Equipment implementation.

  Args:
    ip: local ip address to bind to. If None, find address automatically.
    cpe: the api_soap.cpe object for this device
    listenport: the port number to listen on for ACS ping requests.
    acs_url: An ACS URL to use. This overrides platform_config.GetAcsUrl()
    ping_path: URL path for the ACS Ping function
    fetch_args: kwargs to pass to HTTPClient.fetch
  """

  def __init__(self, ip, cpe, listenport, acs_config,
               ping_path, acs_url=None, fetch_args=None,
               ioloop=None, restrict_acs_hosts=None):
    tornado.httpclient.AsyncHTTPClient.configure(
        'tornado.curl_httpclient.CurlAsyncHTTPClient')
    # pylint:disable=protected-access
    oldcreate = tornado.curl_httpclient._curl_create
    tornado.curl_httpclient._curl_create = (
        lambda *args, **kwargs: CurlCreator(oldcreate, *args, **kwargs))
    # pylint:enable=protected-access
    self.cpe = cpe
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.encode = api_soap.Encode()
    self.cwmplogger = cwmplog.Logger(full_logs=10)
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.event_queue = LimitDeque(MAX_EVENT_QUEUE_SIZE, self.EventQueueHandler)
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.retry_count = 0  # for Inform.RetryCount
    self.start_session_timeout = None  # timer for CWMPRetryInterval
    self.session = None
    self.my_configured_ip = ip
    self.fetch_args = fetch_args or dict()
    self.ping_rate_limit_seconds = 2
    self.previous_ping_time = 0
    self.ping_timeout_pending = None
    self._changed_parameters = set()
    self._changed_parameters_sent = set()
    self._acs_config = acs_config
    self.cpe_management_server = cpe_management_server.CpeManagementServer(
        acs_url=acs_url, acs_config=acs_config, port=listenport,
        ping_path=ping_path, get_parameter_key=cpe.getParameterKey,
        start_periodic_session=self.NewPeriodicSession, ioloop=self.ioloop,
        restrict_acs_hosts=restrict_acs_hosts)
    self.last_success_response = 0  # used by DiagUI
    self.num_599_responses = 0
    self._acs_disabled_until = None

    try:
      notifier = filenotifier.FileNotifier(mainloop.MainLoop())
      self.watch_acs_disabled = notifier.WatchObj(self._AcsDisabledFilename(),
                                                  self._UpdateAcsDisabled)
      self._UpdateAcsDisabled()
    except pyinotify.WatchManagerError:
      print 'cwmp temp dir (%s) does not exist' % CWMP_TMPDIR

  def EventQueueHandler(self):
    """Called if the event queue goes beyond the maximum threshold."""
    print 'Event queue has grown beyond the maximum size, restarting...'
    print 'event_queue=%s' % (str(self.event_queue))
    sys.exit(1)

  def GetManagementServer(self):
    """Return the ManagementServer implementation for tr-98/181."""
    return self.cpe_management_server

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def SendResponse(self, req):
    self.response_queue.append(str(req))
    self.Run()

  def LookupDevIP6(self):
    """Returns the global IPv6 address for the named interface."""
    name = helpers.Activewan(GETWANPORT)
    if not name:
      return 0

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
    """Get the local socket address we *would* use if we were connected."""
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    ip6dev = self.LookupDevIP6()
    if ip6dev:
      return ip6dev
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
    except socket.error:
      pass
    return s.getsockname()[0]

  def EncodeInform(self):
    """Return an Inform message for this session."""
    if not self.session.my_ip:
      my_ip = self._GetLocalAddr()
      self.session.my_ip = my_ip
      self.cpe_management_server.my_ip = my_ip
    events = []
    for ev in self.event_queue:
      events.append(ev)
    parameter_list = []
    try:
      ms = self.cpe.root.obj.InternetGatewayDevice.ManagementServer
      di = self.cpe.root.obj.InternetGatewayDevice.DeviceInfo
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
      # NOTE(jnewlin): Changed parameters can be set to be sent either
      # explicitly with a value change event, or to be sent with the
      # periodic inform.  So it's not a bug if there is no value change
      # event in the event queue.

      # Take all of the parameters and union them with another set that has
      # been previously sent.  When we receive an inform from the ACS we clear
      # the _sent version.  This fixes a bug where we send this list of params
      # to the ACS, followed by a PerioidStat adding itself to the list here,
      # followed by getting an ack from the ACS where we clear the list.  Now
      # we just clear the list of the params that was sent when the ACS acks.
      self._changed_parameters_sent.update(self._changed_parameters)
      self._changed_parameters.clear()
      if self._changed_parameters_sent:
        # Per spec: Whenever a parameter change is sent in the Inform message
        # due to a non-zero Notification setting, the Event code "4 VALUE
        # CHANGE" MUST be included in the list of Events.
        vc_event = ('4 VALUE CHANGE', None)
        if vc_event not in events:
          events.append(vc_event)
        parameter_list += self._changed_parameters_sent
    except (AttributeError, KeyError):
      pass
    req = self.encode.Inform(root=self.cpe.root, events=events,
                             retry_count=self.retry_count,
                             parameter_list=parameter_list)
    return str(req)

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime, event_code):
    if not self.session:
      tc = ('7 TRANSFER COMPLETE', None)
      if tc not in self.event_queue:
        self.event_queue.appendleft(tc)
      self.event_queue.append((event_code, command_key))
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    self.Send(cmpl)

  def GetNext(self):
    """Return next request to process."""
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
    """Run one transaction with the ACS."""
    print 'RUN'
    if not self.session:
      print 'No ACS session, returning.'
      return
    if not self.session.acs_url:
      print 'No ACS URL populated, returning.'
      self._ScheduleRetrySession(wait=60)
      return
    if self.session.should_close():
      print 'Idle CWMP session, terminating.'
      self.outstanding = None
      ping_received = self.session.close()
      self._acs_config.AcsAccessSuccess(self.session.acs_url)
      self.session = None
      self.retry_count = 0  # Successful close
      if self._changed_parameters:
        # Some values triggered during the prior session, start a new session
        # with those changed params.  This should also satisfy a ping.
        self.NewValueChangeSession()
      elif ping_received:
        # Ping received during session, start another
        self._NewPingSession()
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
      headers['Cookie'] = self.session.cookies.output(attrs=[],
                                                      header='', sep=';')
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      # Empty message
      self.session.state_update(cpe_to_acs_empty=True)
    self._acs_config.AcsAccessAttempt(self.session.acs_url)
    print 'CPE POST (at %s):' % time.ctime()
    print 'ACS URL: %s\n' % self.session.acs_url
    print self.cwmplogger.LogSoapXML(self.outstanding)
    req = tornado.httpclient.HTTPRequest(
        url=self.session.acs_url, method='POST', headers=headers,
        body=self.outstanding, follow_redirects=True, max_redirects=5,
        request_timeout=30.0, use_gzip=True, allow_ipv6=True,
        **self.fetch_args)
    self.session.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
    """Callback function invoked with the response an HTTP query to the ACS."""
    self.outstanding = None
    print 'CPE RECEIVED (at %s):' % time.ctime()
    print 'Effective URL was: %r' % response.effective_url
    if not self.session:
      print 'Session terminated, ignoring ACS message.'
      return
    if not response.error:
      self.last_success_response = time.ctime()
      print self.cwmplogger.LogSoapXML(response.body)
      self.cpe_management_server.SuccessfulSession()
      for cookie in response.headers.get_list('Set-Cookie'):
        self.session.cookies.load(cookie)
      if response.body:
        out = self.cpe_soap.Handle(response.body)
        if out is not None:
          self.SendResponse(out)
        # TODO(dgentry): $SPEC3 3.7.1.6 ACS Fault 8005 == retry same request
      else:
        self.session.state_update(acs_to_cpe_empty=True)
      if self.session.acs_url != response.effective_url:
        url = response.effective_url
        print 'Redirecting to %s for remainder of CWMP session' % url
        self.session.acs_url = url
    else:
      print 'HTTP ERROR {0!s}: {1}'.format(response.code, response.error)
      self._ScheduleRetrySession()
    self._HandleSessionEnd(response.code)
    self.Run()
    return 200

  def _ScheduleRetrySession(self, wait=None):
    """Start a timer to retry a CWMP session.

    Args:
      wait: Number of seconds to wait. If wait=None, choose a random wait
        time according to $SPEC3 section 3.2.1
    """
    if self.session:
      self.session.close()
      self.session = None
    if wait is None:
      self.retry_count += 1
      wait = self.cpe_management_server.SessionRetryWait(self.retry_count)
    self.start_session_timeout = self.ioloop.add_timeout(
        datetime.timedelta(seconds=wait), self._SessionWaitTimer)

  def _SessionWaitTimer(self):
    """Handler for the CWMP Retry timer, to start a new session."""
    self.start_session_timeout = None
    self.session = session.CwmpSession(
        acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
    self.Run()

  def _CancelSessionRetries(self):
    """Cancel any pending CWMP session retry."""
    if self.start_session_timeout:
      self.ioloop.remove_timeout(self.start_session_timeout)
      self.start_session_timeout = None
    self.retry_count = 0

  def _NewSession(self, reason):
    if self._AcsDisabled():
      self._CancelSessionRetries()
      # Touch this file so that alivemonitor doesn't kill us.
      self._acs_config.AcsAccessAttempt(self.cpe_management_server.URL)
    elif not self.session:
      self._CancelSessionRetries()
      self.event_queue.appendleft((reason, None))
      self.session = session.CwmpSession(
          acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
      self.Run()

  def _NewTimeoutPingSession(self):
    if self.ping_timeout_pending:
      self.ping_timeout_pending = None
      self._NewPingSession()

  def _NewPingSession(self):
    """Start a new session in response to a ping request."""
    if self.session:
      # $SPEC3 3.2.2 initiate at most one new session after this one closes.
      self.session.ping_received = True
      return

    # Rate limit how often new sessions can be started with ping to
    # once a minute
    current_time = monohelper.monotime()
    elapsed_time = current_time - self.previous_ping_time
    allow_ping = (elapsed_time < 0 or
                  elapsed_time > self.ping_rate_limit_seconds)
    if allow_ping:
      self.ping_timeout_pending = None
      self.previous_ping_time = current_time
      # This happens if there was a previous ping, but ACS failed
      # to respond (503 for example).  And we don't want multiple
      # copies of this event code in the request.
      self.event_queue = self._RemoveFromDequeue(
          self.event_queue, frozenset(['6 connection request']))
      self._NewSession('6 CONNECTION REQUEST')
    elif not self.ping_timeout_pending:
      # Queue up a new session via tornado.
      callback_time = self.ping_rate_limit_seconds - elapsed_time
      if callback_time < 1:
        callback_time = 1
      self.ping_timeout_pending = self.ioloop.add_timeout(
          datetime.timedelta(seconds=callback_time),
          self._NewTimeoutPingSession)

  def NewPeriodicSession(self):
    # If the ACS stops responding for some period of time, it's possible
    # that we'll already have a periodic inform queued up.
    # In this case, don't start the new inform, wait for the session
    # retry.  The retry has a maximum timer of periodic session.
    reason = '2 PERIODIC'
    if (reason, None) not in self.event_queue:
      self._NewSession(reason)

  def NewWakeupSession(self):
    # Some external process may request a new session because e.g. the network
    # just came up.  If we already have such a session in the queue, there's no
    # need to add a second one.
    reason = '6 CONNECTION REQUEST'
    if (reason, None) not in self.event_queue:
      self._NewSession(reason)

  def SetNotificationParameters(self, parameters):
    """Set the list of parameters that have changed.

    The list of parameters that have triggered and should be sent either
    with the next periodic inform, or the next active active value change
    session.

    Args:
      parameters: An array of the parameters that have changed, these
      need to be sent to the ACS in the parameter list.
    """
    for param in parameters:
      self._changed_parameters.add(param)

  def NewValueChangeSession(self):
    """Start a new session to the ACS for the parameters that have changed."""

    # If all the changed parameters have been reported, or there is already
    # a session running, don't do anything.  The run loop for the session
    # will autmatically kick off a new session if there are new changed
    # parameters.
    if not self._changed_parameters or self.session:
      return

    reason = '4 VALUE CHANGE'
    if (reason, None) not in self.event_queue:
      self._NewSession(reason)

  def PingReceived(self):
    self._NewPingSession()
    return 204  # No Content

  def _RemoveFromDequeue(self, dq, rmset):
    """Return a new deque which removes events in rmset."""
    newdq = collections.deque()
    for event in dq:
      (reason, unused_command_key) = event
      if reason.lower() not in rmset:
        newdq.append(event)
    return newdq

  def _HandleSessionEnd(self, code):
    """Called when a session ends, to handle persistent errors.

    If we get too many 599 errors in a row, exit the process
    (and expect a process babysitter to restart it).

    Args:
      code: the error code from the HTTP response.
        599 is generated by Tornado, and indicates an internal problem.
    """
    if code == 599:
      self.num_599_responses += 1
      if self.num_599_responses > 10:
        print 'Too many 599 responses, exiting process.'
        sys.exit(1)
    else:
      self.num_599_responses = 0

  def TransferCompleteReceived(self):
    """Called when the ACS sends a TransferCompleteResponse."""
    reasons = frozenset(['7 transfer complete', 'm download',
                         'm scheduledownload', 'm upload'])
    self.event_queue = self._RemoveFromDequeue(self.event_queue, reasons)

  def InformResponseReceived(self):
    """Called when the ACS sends an InformResponse."""
    reasons = frozenset(['0 bootstrap', '1 boot', '2 periodic',
                         '3 scheduled', '4 value change',
                         '6 connection request', '8 diagnostics complete',
                         'm reboot', 'm scheduleinform'])
    self.event_queue = self._RemoveFromDequeue(self.event_queue, reasons)
    self._changed_parameters_sent.clear()

  def Startup(self):
    rb = self.cpe.download_manager.RestoreReboots()
    if rb:
      self.event_queue.extend(rb)
    self._NewSession('0 BOOTSTRAP')
    # This will call SendTransferComplete, so we have to already be in
    # a session.
    self.cpe.startup()

  def _AcsDisabled(self):
    return (self._acs_disabled_until is not None and
            time.time() < self._acs_disabled_until)

  def _UpdateAcsDisabled(self):
    filename = self._AcsDisabledFilename()
    if os.path.exists(filename):
      self._acs_disabled_until = (os.stat(filename).st_mtime +
                                  ACS_DISABLE_EXPIRY_SECS)
      print ('ACS sessions suspended for %d seconds' %
             (self._acs_disabled_until - time.time()))
    else:
      self._acs_disabled_until = None

  def _AcsDisabledFilename(self):
    return os.path.join(CWMP_TMPDIR, DISABLE_ACS_FILE)


def Listen(ip, port, ping_path, acs, cpe, cpe_listener, acs_config,
           acs_url=None, fetch_args=None, ioloop=None,
           restrict_acs_hosts=None):
  """Listens for "pings" that start a new session with the ACS."""
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  fetch_args = fetch_args or dict()
  cpe_machine = CPEStateMachine(ip=ip, cpe=cpe, listenport=port,
                                ping_path=ping_path,
                                acs_config=acs_config,
                                restrict_acs_hosts=restrict_acs_hosts,
                                acs_url=acs_url,
                                fetch_args=fetch_args, ioloop=ioloop)
  cpe.setCallbacks(
      send_transfer_complete=cpe_machine.SendTransferComplete,
      transfer_complete_received=cpe_machine.TransferCompleteReceived,
      inform_response_received=cpe_machine.InformResponseReceived,
      set_notification_parameters=cpe_machine.SetNotificationParameters,
      new_value_change_session=cpe_machine.NewValueChangeSession)
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
                     dict(cpe_ms=cpe_machine.cpe_management_server,
                          callback=cpe_machine.PingReceived)))
    print 'TR-069 callback at http://*:%d/%s' % (port, ping_path)
  webapp = tornado.web.Application(handlers)
  webapp.listen(port)
  return cpe_machine
