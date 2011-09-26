#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import random
import api_soap
import soap
import tornadi_fix       #pylint: disable-msg=W0611
import tornado.httpclient
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
  return result.body


class PingHandler(tornado.web.RequestHandler):
  def __init__(self, cpe, *args, **kwargs):
    self.cpe = cpe
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.cpe._PingReceived()


class Handler(tornado.web.RequestHandler):
  def __init__(self, soap_handler, *args, **kwargs):
    self.soap_handler = soap_handler
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.write("this is the cpe")

  def post(self):
    print 'TR-069 server: request received:\n%s' % self.request.body
    result = self.soap_handler(self.request.body)
    self.write(str(result))


def Listen(port, ping_path, cpe, acs):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(128)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  handlers = []
  if acs:
    acshandler = api_soap.ACS(acs).Handle
    handlers.append(('/acs', lambda *args: Handler(acshandler, *args)))
    print 'TR-069 ACS at http://localhost:%d/acs' % port
  if cpe:
    cpehandler = api_soap.CPE(cpe).Handle
    handlers.append(('/cpe', lambda *args: Handler(cpehandler, *args)))
    print 'TR-069 CPE at http://localhost:%d/cpe' % port
  if ping_path:
    handlers.append(('/' + ping_path, lambda *args: PingHandler(cpe, *args)))
    print 'TR-069 callback at http://localhost:%d/%s' % (port, ping_path)
  webapp = tornado.web.Application(handlers)
  webapp.listen(port)


def main():
  with soap.Envelope(1234, False) as xml:
    #soap.GetParameterNames(xml, '', True)
    xml.GetRPCMethods(None)
  print 'Response:'
  print SyncClient('http://localhost:7547/cpe', xml)


if __name__ == '__main__':
  main()
