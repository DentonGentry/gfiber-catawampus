#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import bup.shquote
import mainloop


class QuotedBlockProtocol(object):
  def __init__(self, handle_lines_func):
    self.handle_lines_func = handle_lines_func
    self.partial_line = ''
    self.lines = []

  def GotData(self, bytes):
    line = self.partial_line + bytes
    firstchar, word = bup.shquote.unfinished_word(line)
    if word:
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
    for line in (lines or []):
      out.append(bup.shquote.quotify_list(line) + '\r\n')
    out.append('\r\n')
    return ''.join(out)


class QuotedBlockStreamer(object):
  def __init__(self, sock, address):
    self.sock = sock
    self.address = address
    qb = QuotedBlockProtocol(self.ProcessBlock)
    mainloop.LineReader(sock, address, qb.GotData)

  def ProcessBlock(self, lines):
    print 'lines: %r' % (lines,)
    return [['RESPONSE:']] + lines + [['EOR']]


def main():
  loop = mainloop.MainLoop()
  loop.ListenInet6(('', 12999), QuotedBlockStreamer)
  loop.ListenUnix('/tmp/mainloop.sock', QuotedBlockStreamer)
  print 'hello'
  loop.Start()
  

if __name__ == "__main__":
  main()
