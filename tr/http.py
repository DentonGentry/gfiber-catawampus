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
import soap
import tornadi_fix       #pylint: disable-msg=W0611
import tornado.httpclient
import tornado.web


def SyncClient(url, postdata):
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
  def get(self):
    self.write("hello, world")


class CpeHandler(tornado.web.RequestHandler):
  def __init__(self, cpe, *args, **kwargs):
    self.cpe = cpe
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.write("this is the cpe")

  def post(self):
    obj = soap.Parse(self.request.body)
    print 'cpe request received:\n%s' % obj
    reqid = obj.Header.get('ID', None)
    req = obj.Body[0]
    if req.name == 'GetParameterNames':
      names = list(self.cpe.GetParameterNames(str(req.ParameterPath),
                                              int(req.NextLevel)))
      with soap.Envelope(request_id=reqid, hold_requests=None) as xml:
        with xml['cwmp:GetParameterNamesResponse']:
          for name in names:
            with xml['ParameterInfoStruct']:
              xml.Name(name)
              xml.Writable('1')
      self.write(str(xml))


class AcsHandler(tornado.web.RequestHandler):
  def __init__(self, acs, *args, **kwargs):
    self.acs = acs
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.write("this is the acs")

  def post(self):
    obj = soap.Parse(self.request.body)
    self.write('acs request received: data=%r' % obj)


def Listen(port, ping_path, cpe, acs):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(128)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  handlers = []
  if acs:
    handlers.append(('/acs', lambda *args: AcsHandler(acs, *args)))
    print 'TR-069 ACS at http://localhost:%d/acs' % port
  if cpe:
    handlers.append(('/cpe', lambda *args: CpeHandler(cpe, *args)))
    print 'TR-069 CPE at http://localhost:%d/cpe' % port
  if ping_path:
    handlers.append(('/' + ping_path, PingHandler))
    print 'TR-069 callback at http://localhost:%d/%s' % (port, ping_path)
  webapp = tornado.web.Application(handlers)
  webapp.listen(port)


def main():
  with soap.Envelope(1234, False) as xml:
    postdata = soap.GetParameterNames(xml, '', True)
  print 'Response:'
  print SyncClient('http://localhost:7547/cpe', postdata)


if __name__ == '__main__':
  main()
