#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import time
import random
import api_soap
import soap
import tornadi_fix       #pylint: disable-msg=W0611
import tornado.httpclient
import tornado.ioloop
import tornado.web


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
  result = cli.fetch(url, method="POST", headers=headers, body=postdata)
  print result.body
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
  def __init__(self, cpe, acs_url):
    self.cpe = cpe
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.acs_url = acs_url
    self.encode = api_soap.Encode()
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.on_hold = False  # TODO(apenwarr): actually set this somewhere
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.http = tornado.httpclient.AsyncHTTPClient(io_loop=self.ioloop)
    self.cookies = None

  def Send(self, req):
    print 'CPE SENT (at %s):' % time.ctime()
    print str(req)
    self.request_queue.append(str(req))
    self.Run()

  def SendInform(self, reason):
    events = [(reason, '')]
    req = self.encode.Inform(('manufacturer', 'oui', 'productclass',
                              'serialnumber'),
                             events=events,
                             max_envelopes=1, current_time=None,
                             retry_count=1, parameter_list=[])
    return self.Send(req)

  def GetNext(self):
    if self.response_queue:
      return self.response_queue.pop(0)
    elif self.request_queue and not self.on_hold:
      return self.request_queue.pop(0)

  def Run(self):
    print 'RUN'
    if self.outstanding is None:
      self.outstanding = self.GetNext()
    headers = {}
    if self.cookies:
      headers['Cookie'] = ";".join(self.cookies)
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      self.outstanding = ''
    print "CPE POST: %r\n%s" % (str(headers), self.outstanding)
    self.http.fetch(self.acs_url, self.GotResponse, method="POST",
                    headers=headers, body=self.outstanding)

  def GotResponse(self, response):
    was_outstanding = self.outstanding
    self.outstanding = None
    print 'CPE RECEIVED (at %s):' % time.ctime()
    cookies = response.headers.get_list("Set-Cookie")
    if cookies:
      self.cookies = cookies
    print response.body
    if response.body:
      out = self.cpe_soap.Handle(response.body)
      if out is not None:
        self.Send(out)
        self.Run()
    if (was_outstanding or 
        self.response_queue or 
        (self.request_queue and not self.on_hold)):
      self.Run()

  def PingReceived(self):
    # TODO(apenwarr): make sure we flush cookies at each session start.
    # For now, PingReceived is the only way we start a session, so here is
    # okay.
    self.cookies = None
    self.SendInform('6 CONNECTION REQUEST')


def Listen(port, ping_path, acs, acs_url, cpe, cpe_listener):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(128)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  handlers = []
  if acs:
    acshandler = api_soap.ACS(acs).Handle
    handlers.append(('/acs', Handler, dict(soap_handler=acshandler)))
    print 'TR-069 ACS at http://*:%d/acs' % port
  if cpe and cpe_listener:
    cpehandler = api_soap.CPE(cpe).Handle
    handlers.append(('/cpe', Handler, dict(soap_handler=cpehandler)))
    print 'TR-069 CPE at http://*:%d/cpe' % port
  cpe_machine = CPEStateMachine(cpe, acs_url)
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
