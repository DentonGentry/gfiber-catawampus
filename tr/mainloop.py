#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""An application mainloop based on tornado.ioloop.

This lets us build single-threaded async networking applications that can
listen on sockets, connect to sockets, implement a tornado web server, and
so on.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import errno
import os
import socket
import time
import tornado.ioloop
import tornado.iostream  #pylint: disable-msg=W0404


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
  """Return a new listening socket on the given family and address."""
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
  """A class for listening on a socket using the mainloop.

  We create the requested socket, bind() it, listen() it, register it
  with tornado, and then accept() on it whenever an incoming connection
  arrives.  Then we pass the incoming connection to the given callback.
  """

  def __init__(self, family, address, onaccept_func):
    """Initialize a ListenSocket.

    Args:
      family: eg. socket.AF_INET, socket.AF_INET6, socket.AF_UNIX
      address: eg. ('0.0.0.0', 1234) or '/tmp/unix/socket/path'
      onaccept_func: called with newly-accepted socket, with parameters
        (address, sock).
    """
    self.onaccept_func = onaccept_func
    self.family = family
    self.address = address
    self.sock = None
    self.sock = _ListenSocket(family, address)
    self.address = self.sock.getsockname()[:2]
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_handler(self.sock.fileno(), self._Accept, ioloop.READ)

  def __del__(self):
    print 'deleting listener: %r' % (self.address,)
    if self.family == socket.AF_UNIX and self.sock:
      self.sock.close()
      _Unlink(self.address)

  def _Accept(self, fd, events):  #pylint: disable-msg=W0613
    try:
      sock, address = self.sock.accept()
    except socket.error, e:
      if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
        return
      raise
    sock.setblocking(0)  #pylint: disable-msg=E1101
    print 'got a connection from %r' % (address,)
    self.onaccept_func(sock, address)


class LineReader(object):
  """A helper for sockets that read newline-delimited data.

  We register with the mainloop to get called whenever incoming data arrives
  on the socket.  Then, we call a callback for each line (ie. text ending
  in newline) we receive.
  """

  def __init__(self, sock, address, gotline_func):
    """Initialize a LineReader.

    Args:
      sock: a socket.socket() object.
      address: the remote address of the socket.
      gotline_func: called for each line of data, with parameter (line).
    """
    self.address = address
    self.gotline_func = gotline_func
    self.stream = tornado.iostream.IOStream(sock)
    self.stream.set_close_callback(self.OnClose)
    self._StartRead()

  def __del__(self):
    print 'deleting linereader: %r' % (self.address,)

  def _StartRead(self):
    self.stream.read_until('\n', self.GotData)

  def GotData(self, line):
    try:
      result = self.gotline_func(line)
      if result:
        self.Write(result)
    finally:
      self._StartRead()

  def Write(self, bytestring):
    return self.stream.write(bytestring)

  def OnClose(self):
    print 'closing %r' % (self.address,)
    self.stream._read_callback = None
    self.stream.set_close_callback(None)


class MainLoop(object):
  """A slightly more convenient wrapper for tornado.ioloop.IOLoop."""

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
    """Run the mainloop repetitively until the program is finished.

    "Finished" means one of three things: no event handlers remain (unlikely),
    the timeout expires, or someone calls ioloop.stop().

    Args:
      timeout: the time at which the loop will be forcibly stopped.  Mostly
        useful in unit tests.  None means no timeout; 0 means stop instantly.
    """
    tmo = None
    if timeout is not None:
      deadline = time.time() + timeout
      self.loop_timeout = tmo = self.ioloop.add_timeout(deadline,
                                                        self._TimedOut)
    try:
      self.ioloop.start()
    finally:
      if tmo:
        self.ioloop.remove_timeout(tmo)
        self.loop_timeout = None

  def RunOnce(self, timeout=None):
    """Run the mainloop for exactly one iteration.

    Processes all events that occur during that iteration, including
    timeouts.

    Args:
      timeout: same meaning as in Start().
    """
    r, w = os.pipe()
    try:
      os.write(w, 'x')
      self.ioloop.add_handler(r, lambda fd, events: self.ioloop.stop(),
                              self.ioloop.READ)
      self.Start(timeout)
    finally:
      os.close(r)
      os.close(w)
      self.ioloop.remove_handler(r)

  def _TimedOut(self):
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
    return self.Connect(socket.AF_UNIX, filename, onconnect_func)


def _TestGotLine(line):
  print 'got line: %r' % line
  return 'response\r\n'


def main():
  loop = MainLoop()
  #pylint: disable-msg=C6402
  loop.ListenInet6(('', 12999),
                   lambda sock, address: LineReader(sock, address,
                                                    _TestGotLine))
  print 'hello'
  loop.Start()


if __name__ == '__main__':
  main()
