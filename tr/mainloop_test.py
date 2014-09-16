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

"""Test app for mainloop stuff."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import select
import socket
import unittest
import weakref

import google3
import tornado.ioloop
import mainloop


REQUEST_STRING = 'this is the request\n'


idler = [0,0]


@mainloop.WaitUntilIdle
def IdleFunc():
  print 'i0'
  idler[0] += 1


class IdleClass(object):
  @mainloop.WaitUntilIdle
  def ClassIdleFunc(self):
    print 'i1: %r' % self
    idler[1] += 1


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
    if stream:
      stream.write(REQUEST_STRING)

  def testMainLoop(self):
    self.got = ''
    loop = mainloop.MainLoop()
    listener = loop.ListenInet(('', 0), self._MakeHandler)
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

  def testMainLoop2(self):
    loop = mainloop.MainLoop()
    loop.RunOnce()
    del loop
    loop = mainloop.MainLoop()
    loop.RunOnce()

  def testIdler(self):
    print
    print 'testIdler'
    loop = mainloop.MainLoop()
    loop.RunOnce()
    idler[0] = 0
    idler[1] = 0
    IdleFunc()
    IdleFunc()
    loop.RunOnce()
    self.assertEquals(idler, [1, 0])
    loop.RunOnce()
    self.assertEquals(idler, [1, 0])
    i1 = IdleClass()
    i2 = IdleClass()
    i1.ClassIdleFunc()
    i1.ClassIdleFunc()
    i2.ClassIdleFunc()
    i2.ClassIdleFunc()
    loop.RunOnce()
    self.assertEquals(idler, [1, 2])

  def testReentrance(self):
    print
    print 'testReentrance'
    loop = mainloop.MainLoop()
    loop.RunOnce()
    s1, s2 = socket.socketpair()
    s2.send('x')
    select.select([s1], [], [])
    # Now the 'x' has reached s1

    def Handler(fd, events):
      loop.ioloop.remove_handler(fd)
      # NOTE(apenwarr): This simulates a case where epoll (or something)
      #   somehow returns an event to tornado even after the handler has
      #   been unregistered for that fd.  I don't see how that can possibly
      #   happen, but apparently it does in the field.  I can't find a way
      #   to reproduce it normally, so we fake it by just adding the current
      #   event back in.
      loop.ioloop._events[fd] = events
    loop.ioloop.add_handler(s1.fileno(), Handler, loop.ioloop.READ)
    loop.RunOnce()
    loop.RunOnce()

    self.assertEquals(s1.recv(1), 'x')

if __name__ == '__main__':
  unittest.main()
