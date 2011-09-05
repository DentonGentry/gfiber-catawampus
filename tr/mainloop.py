#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import errno
import os
import socket
import sys
import time
import tornado.ioloop
import tornado.iostream


def _Unlink(filename):
  try:
    os.unlink(filename)
  except OSError, e:
    if e.errno != errno.ENOENT:
      raise


def _DeleteOldSock(family, address):
  tsock = socket.socket(family, socket.SOCK_STREAM, 0)
  try:
    tsock.connect(address)
  except socket.error, e:
    if e.errno == errno.ECONNREFUSED:
      _Unlink(address)


def _ListenSocket(family, address):
  sock = socket.socket(family, socket.SOCK_STREAM, 0)
  if family == socket.AF_UNIX:
    _DeleteOldSock(family, address)
  else:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setblocking(0)
  sock.bind(address)
  sock.listen(10)
  return sock
  

class ListenSocket(object):
  def __init__(self, family, address, onaccept_func):
    self.onaccept_func = onaccept_func
    self.family = family
    self.address = address
    self.sock = None
    self.sock = _ListenSocket(family, address)
    self.address = self.sock.getsockname()[:2]
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_handler(self.sock.fileno(), self.Accept, ioloop.READ)

  def __del__(self):
    print 'deleting listener: %r' % (self.address,)
    if self.family == socket.AF_UNIX and self.sock:
      self.sock.close()
      _Unlink(self.address)

  def Accept(self, fd, events):
    try:
      sock, address = self.sock.accept()
    except socket.error, e:
      if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
        return
      raise
    sock.setblocking(0)
    print 'got a connection from %r' % (address,)
    self.onaccept_func(sock, address)


class LineReader(object):
  def __init__(self, sock, address, gotline_func):
    self.address = address
    self.gotline_func = gotline_func
    self.stream = tornado.iostream.IOStream(sock)
    self.stream.set_close_callback(self.OnClose)
    #self.OnClose()
    #self.stream.set_close_callback(None)
    self._StartRead()

  def __del__(self):
    print 'deleting linereader: %r' % (self.address,)

  def _StartRead(self):
    self.stream.read_until('\n', self.GotData)

  def GotData(self, bytes):
    try:
      result = self.gotline_func(bytes)
      if result:
        self.Write(result)
    finally:
      self._StartRead()

  def Write(self, bytes):
    return self.stream.write(bytes)

  def OnClose(self):
    print 'closing'
    self.stream._read_callback = None
    self.stream.set_close_callback(None)


class MainLoop(object):
  def __init__(self):
    self.ioloop = None
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.loop_timeout = None

  def __del__(self):
    # we have to do this so objects who have registered with the ioloop
    # can get their refcounts down to zero, so their destructors can be
    # called
    if self.ioloop:
      self.ioloop._handlers = None
      self.ioloop._events = None

  def Start(self, timeout=None):
    tmo = None
    if timeout is not None:
      deadline = time.time() + timeout
      self.loop_timeout = tmo = self.ioloop.add_timeout(deadline, self.TimedOut)
    try:
      return self.ioloop.start()
    finally:
      if tmo:
        self.ioloop.remove_timeout(tmo)
        self.loop_timeout = None

  def RunOnce(self, timeout=None):
    r, w = os.pipe()
    try:
      os.write(w, 'x')
      self.ioloop.add_handler(r, lambda fd,events: self.ioloop.stop(),
                              self.ioloop.READ)
      self.Start(timeout)
    finally:
      os.close(r)
      os.close(w)
      self.ioloop.remove_handler(r)

  def TimedOut(self):
    self.ioloop.stop()
    self.ioloop.remove_timeout(self.loop_timeout)
    self.loop_timeout = None

  def Listen(self, family, address, onaccept_func):
    return ListenSocket(family, address, onaccept_func)

  def ListenInet6(self, address, onaccept_func):
    return self.Listen(socket.AF_INET6, address, onaccept_func)

  def ListenUnix(self, filename, onaccept_func):
    return self.Listen(socket.AF_UNIX, filename, onaccept_func)

  def Connect(self, family, address, onconnect_func):
    sock = socket.socket(family, socket.SOCK_STREAM, 0)
    stream = tornado.iostream.IOStream(sock)
    stream.connect(address, lambda: onconnect_func(stream))
    return stream

  def ConnectInet6(self, address, onconnect_func):
    return self.Connect(socket.AF_INET6, address, onconnect_func)

  def ConnectUnix(self, filename, onconnect_func):
    return self.Connect(socket.AF_UNIX, address, onconnect_func)


def _TestGotLine(line):
  print 'got line: %r' % line
  return 'response\r\n'


def main():
  loop = MainLoop()
  loop.ListenInet6(('', 12999),
                   lambda sock, address: LineReader(sock, address,
                                                    _TestGotLine))
  print 'hello'
  loop.Start()


if __name__ == "__main__":
  main()
