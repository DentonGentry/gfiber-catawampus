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
import tornadi_fix       #pylint: disable-msg=W0611
import tornado.web


class PingHandler(tornado.web.RequestHandler):
  def get(self):
    self.write("hello, world")


class CpeHandler(tornado.web.RequestHandler):
  def __init__(self, cpe, *args, **kwargs):
    self.cpe = cpe
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.write("this is the cpe")


class AcsHandler(tornado.web.RequestHandler):
  def __init__(self, acs, *args, **kwargs):
    self.acs = acs
    tornado.web.RequestHandler.__init__(self, *args, **kwargs)
    
  def get(self):
    self.write("this is the acs")



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
  
