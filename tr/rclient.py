#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""Command-line client for rcommand.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import os.path
import re
import readline
import socket
import sys
import bup.shquote
import mainloop
import quotedblock


HISTORY_FILE = os.path.expanduser('~/.rclient_history')


class Fatal(Exception):
  pass


def HandleFatal(func):
  def Fn(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except Fatal, e:
      sys.stderr.write('Fatal: %s\n' % e)
      sys.exit(1)
  return Fn


class Client(object):
  def __init__(self, loop):
    self.loop = loop
    self.stream = None
    self.quotedblock = quotedblock.QuotedBlockProtocol(
                                      HandleFatal(self.GotBlock))
    self._StartConnect()

  def _StartConnect(self):
    self.stream = None
    try:
      self.loop.ConnectUnix('/tmp/mainloop.sock',
                            HandleFatal(self.OnConnect))
    except socket.error, e:
      raise Fatal(str(e))

  def Close(self):
    if self.stream:
      self.stream.close()

  def OnConnect(self, stream):
    print 'Connected to server.'
    self.stream = stream
    self.stream.set_close_callback(HandleFatal(self.OnClose))
    self._StartRead()
    self.loop.ioloop.stop()

  def _StartRead(self):
    self.stream.read_until('\n', HandleFatal(self.GotData))

  def OnClose(self):
    print 'Server connection closed!'
    self._StartConnect()

  def GotData(self, data):
    self.quotedblock.GotData(data)
    self._StartRead()

  def GotBlock(self, lines):
    print self.quotedblock.RenderBlock(lines).strip()
    self.loop.ioloop.stop()

  def Send(self, lines):
    s = self.quotedblock.RenderBlock(lines)
    self.stream.write(s)


def _DotsToSlashes(s):
  return re.sub(r'([^/.])\.', r'\1/', s)


def _SlashesToDots(s):
  name = s.replace('/', '.')
  if name.startswith('.'):
    name = name[1:]
  return name


def main():
  if os.path.exists(HISTORY_FILE):
    readline.read_history_file(HISTORY_FILE)
  cwd = '/'
  client = None
  try:
    loop = mainloop.MainLoop()
    client = Client(loop)
    loop.Start()
  
    while True:
      print
      line = raw_input('%s> ' % cwd) + '\n'
      while 1:
        wordstart, word = bup.shquote.unfinished_word(line)
        if not word:
          break
        line += raw_input('%*s> ' % (len(cwd), '')) + '\n'
      words = [word for (idx, word) in bup.shquote.quotesplit(line)]
      if not words:
        continue
      cmd, args = (words[0].lower(), words[1:])
      if cmd in ('cd', 'ls', 'list', 'rlist', 'get', 'set'):
        if not args:
          args = [cwd]
        relpath = _DotsToSlashes(args[0])
        abspath = os.path.normpath(os.path.join(cwd, relpath))
        args[0] = _SlashesToDots(abspath)
      if cmd == 'cd':
        cwd = os.path.normpath(os.path.join(cwd, relpath))
      else:
        line = [cmd] + args
        client.Send([line])
        loop.Start()
  except Fatal, e:
    sys.stderr.write('%s\n' % e)
    sys.exit(1)
  finally:
    readline.write_history_file(HISTORY_FILE)
    if client:
      client.Close()


if __name__ == '__main__':
  main()
    
