#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Test app for mainloop stuff."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import socket
import unittest
import weakref
import mainloop
import tornado.ioloop
import tornado.iostream


REQUEST_STRING = 'this is the request\n'


class MainLoopTest(unittest.TestCase):
  """Tests for mainloop.MainLoop."""
  
  def _GotLine(self, line):
    print 'got line: %r' % (line,)
    tornado.ioloop.IOLoop.instance().stop()
    self.assertEqual(line, REQUEST_STRING)
    self.got += line

  def _MakeHandler(self, sock, request):
    lr = mainloop.LineReader(sock, request, self._GotLine)
    self.handler = weakref.ref(lr)

  def _SendRequest(self, stream):
    stream.write(REQUEST_STRING)
  
  def testMainLoop(self):
    self.got = ''
    loop = mainloop.MainLoop()
    listener = loop.ListenInet6(('', 12999), self._MakeHandler)
    stream = loop.Connect(listener.family, listener.address, self._SendRequest)
    loop.Start(timeout=5)
    print 'after loop 1'
    self.assertEqual(self.got, REQUEST_STRING)
    stream.close()
    print 'after close'
    loop.RunOnce(timeout=5)
    print 'after loop 2'

    # This slightly weird test ensures that the LineReader object actually
    # gets destroyed after its client closes.  If it didn't, we would have
    # a memory leak.  self.handler is itself a weakref so that its own
    # existence doesn't prevent the object from being destroyed, thus
    # defeating our test.
    self.assertEqual(self.handler(), None)


if __name__ == '__main__':
  unittest.main()
