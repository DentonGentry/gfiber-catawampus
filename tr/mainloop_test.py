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

import os
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

  def testFdReplacement(self):
    print
    print 'testFdReplacement'
    loop = mainloop.MainLoop()
    loop.RunOnce()
    s1, s2 = socket.socketpair()
    s3, s4 = socket.socketpair()
    fd = os.dup(s1.fileno())
    print 'fds are: %d %d %d' % (s1.fileno(), s2.fileno(), fd)
    count = [0]
    def Handler(fd, events):
      count[0] += 1
      print 'handler: %r %r count=%d' % (fd, events, count[0])
    loop.ioloop.add_handler(s1.fileno(), Handler, loop.ioloop.READ)
    loop.RunOnce()
    self.assertEquals(count[0], 0)
    s2.close()
    loop.RunOnce()
    self.assertEquals(count[0], 1)
    loop.RunOnce()
    self.assertEquals(count[0], 2)
    # so far so good.  Now replace s1's fd with a totally different
    # (and not active) socket.  s1's endpoint still exists as a copy at
    # 'fd', but s1's original fd, which is the one we're waiting on,
    # is no longer producing events.
    # epoll() and select() diverge in behaviour here; epoll weirdly
    # keeps returning events related to s1 but which report the original fd
    # (now owned by the non-eventful copy of s3).  select() will return
    # nothing if you select on the original fd, because it sees s3, not s1.
    # Phew.
    # Unfortunately libcurl sometimes produces this behaviour (generally,
    # when it closes its http socket and immediately replaces it), so we
    # need to validate that weird things won't happen in that case.
    s1fn = s1.fileno()
    s1.close()
    os.dup2(s3.fileno(), s1fn)
    loop.ioloop.remove_handler(s1fn)
    loop.ioloop.add_handler(s1fn, Handler, loop.ioloop.READ)
    loop.RunOnce()
    self.assertEquals(count[0], 2)


if __name__ == '__main__':
  unittest.main()
