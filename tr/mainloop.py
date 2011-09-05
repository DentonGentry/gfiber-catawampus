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


class LineReader(object):
  def __init__(self, sock, address, gotline_func):
    self.stream = tornado.iostream.IOStream(sock)
    self.address = address
    self.gotline_func = gotline_func
    self._StartRead()

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


class QuotedBlockProtocol(object):
  def __init__(self, handle_lines_func):
    self.handle_lines_func = handle_lines_func
    self.partial_line = ''
    self.lines = []

  def GotData(self, bytes):
    line = self.partial_line + bytes
    firstchar, word = bup.shquote.unfinished_word(line)
    if word:
      print 'unfinished: %r' % word
      self.partial_line = line
    else:
      self.partial_line = ''
      return self.GotLine(line)

  def GotLine(self, line):
    if line.strip():
      # a new line in this block
      parts = bup.shquote.quotesplit(line)
      self.lines.append([word for offset,word in parts])
    else:
      # blank line means end of block
      lines = self.lines
      self.lines = []
      result = self.handle_lines_func(lines)
      return self.RenderBlock(result)

  def RenderBlock(self, lines):
    out = []
    for line in lines:
      out.append(bup.shquote.quotify_list(line) + '\r\n')
    out.append('\r\n')
    return ''.join(out)


def main():
  ioloop = tornado.ioloop.IOLoop.instance()

  def _TestProcessCommand(lines):
    print 'lines: %r' % (lines,)
    return [['RESPONSE:']] + lines + [['EOR']]

  def MakeHandler(sock, address):
    qb = QuotedBlockProtocol(_TestProcessCommand)
    LineReader(sock, address, qb.GotData)
    
  listener = TcpListener(12999, MakeHandler)
  print 'hello'
  ioloop.start()
  

if __name__ == "__main__":
  main()
