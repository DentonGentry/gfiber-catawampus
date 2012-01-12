#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 CWMP Sesion handling."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tornado.httpclient
import tornado.ioloop

# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf

graphviz = r"""
digraph DLstates {
  node [shape=box]

  INIT [label="INIT"]
  ACTIVE [label="ACTIVE\nsend responses or requests"]
  ONHOLD [label="ONHOLD\nsend responses"]
  NOMORE [label="NOMORE\nsend responses"]
  DONE [label="DONE\nclose session"]

  INIT -> ACTIVE [label="Send Inform"]
  ACTIVE -> ONHOLD [label="onhold=True"]
  ONHOLD -> ACTIVE [label="onhold=False"]
  ACTIVE -> NOMORE [label="send empty POST"]
  NOMORE -> DONE [label="receive empty Body"]
}
"""

class CwmpSession(object):
  INIT = "INIT"
  ACTIVE = "ACTIVE"
  ONHOLD = "ONHOLD"
  NOMORE = "NOMORE"
  DONE = "DONE"

  def __init__(self, acs_url, io_loop=None):
    self.http = tornado.httpclient.AsyncHTTPClient(
        max_simultaneous_connections=1,
        io_loop=io_loop or tornado.ioloop.IOLoop.instance())
    self.acs_url = acs_url
    self.cookies = None
    self.my_ip = None
    self.ping_received = False
    self.state = self.INIT

  def state_update(self, sent_inform=None, on_hold=None,
                   cpe_to_acs_empty=None, acs_to_cpe_empty=None):
    if self.state == self.INIT:
      if sent_inform:
        self.state = self.ACTIVE
    elif self._active():
      if on_hold:
        self.state = self.ONHOLD
      elif cpe_to_acs_empty:
        self.state = self.NOMORE
    elif self._onhold():
      if on_hold is False:  # not just the default None; explicitly False
        self.state = self.ACTIVE
    elif self._nomore():
      if acs_to_cpe_empty:
        self.state = self.DONE

  def _init(self):
    return self.state == self.INIT
  def _active(self):
    return self.state == self.ACTIVE
  def _onhold(self):
    return self.state == self.ONHOLD
  def _nomore(self):
    return self.state == self.NOMORE
  def _done(self):
    return self.state == self.DONE

  def inform_required(self):
    return True if self._init() else False

  def request_allowed(self):
    return True if self._active() else False

  def response_allowed(self):
    return False if self._init() or self._done() else True

  def should_close(self):
    return True if self._done() else False

  def __del__(self):
    self.close()

  def close(self):
    self.http = None
    return self.ping_received


def main():
  print("# pipe this to grapviz, ex:")
  print("# ./cwmp_session.py | dot -Tpdf -ocwmp_session.pdf")
  print(graphviz)


if __name__ == '__main__':
  main()
