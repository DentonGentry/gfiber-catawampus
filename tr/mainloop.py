#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import errno
import os
import re
import socket
import bup.shquote
import tornado.ioloop
import tornado.iostream


def _ListenSocket(family, address):
  sock = socket.socket(family, socket.SOCK_STREAM, 0)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setblocking(0)
  sock.bind(address)
  sock.listen(10)
  return sock
  

class TcpListener(object):
  def __init__(self, port, onaccept_func):
    self.onaccept_func = onaccept_func
    self.sock = _ListenSocket(socket.AF_INET6, ("", port))
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_handler(self.sock.fileno(), self.Accept, ioloop.READ)

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


class QuotedBlockReaderWriter(object):
  def __init__(self, sock, address, handler_func):
    self.stream = tornado.iostream.IOStream(sock)
    self.address = address
    self.handler_func = handler_func
    self.lines = []
    self.StartRead()

  def StartRead(self, init_bytes=None):
    if not init_bytes:
      init_bytes = ''
    self.stream.read_until('\n',
                           lambda bytes: self.GotData(init_bytes + bytes))

  def GotLine(self, bytes):
    if not bytes.strip():
      # blank line means end of block
      lines = self.lines
      self.lines = []
      self.handler_func(self, lines)
    else:
      # a new line in this block
      parts = bup.shquote.quotesplit(bytes)
      self.lines.append([word for offset,word in parts])

  def GotData(self, bytes):
    print 'got data from %r' % (self.address,)
    print repr(bytes)
    firstchar, word = bup.shquote.unfinished_word(bytes)
    if word:
      print 'unfinished: %r' % word
      self.StartRead(bytes)
    else:
      self.GotLine(bytes)
      self.StartRead()

  def Write(self, lines):
    for line in lines:
      self.stream.write(bup.shquote.quotify_list(line) + '\r\n')
    self.stream.write('\r\n')


def HandleLines(qbrw, lines):
  print 'lines: %r' % (lines,)
  qbrw.Write([['RESPONSE:']] + lines + [['EOR']])


def main():
  ioloop = tornado.ioloop.IOLoop.instance()
  listener = TcpListener(12999,
                         lambda sock, address:
                           QuotedBlockReaderWriter(sock, address, HandleLines))
  print 'hello'
  ioloop.start()
  


if __name__ == "__main__":
  main()
